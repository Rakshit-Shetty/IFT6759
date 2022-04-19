"""
Reads the configuration file and carries out the instructions to train the desired model.
"""

import argparse
import logging
import os
import torch
import yaml
import numpy as np
import pickle
import logging

logging.basicConfig(level=logging.INFO)

def main(args):
    
    config_path = os.path.join('./Config/',args.config_file)
    with open(config_path) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    
    device = args.device
    num = config['num'] if ('num' in config) else 0
    task = config["task"] if ('task' in config) else 'super' 

    data_file = config["data"]
    model_file = config["model"]
    augment_file = config["augment"] if ("augment" in config) else None 
    augment_strength = config["aug_strength"] if ("aug_strength" in config) else None
    eval_file = config["eval"]

    batch_size = config["batch_size"] if ("batch_size" in config) else 64
    learn_rate = config["learning_rate"] if ("learning_rate" in config) else 0.001
    momentum = config["momentum"] if ("momentum" in config) else 0
    epoch = config["epoch"] if ("epoch" in config) else 10
    optimizer = config["optimizer"] if ("optimizer" in config) else "adam"
    weight_decay = config["weight_decay"] if ("weight_decay" in config) else 0
    seed = config["seed"] if ("weight_decay" in config) else 6942 

    
    
    # Importing function for loading the desired data    
    logging.info(f"==========Dataset: {data_file}==========")
    data_file_path = f"Data.{data_file}"
    _temp = __import__(name=data_file_path, fromlist=['Data_Load'])
    Data_Load = _temp.Data_Load
    
    # Importing the augmentation methods
    if augment_file == None:
        print("No augmentation method selected")
    else:
        Aug = []
        for i in range(len(augment_file)):
            logging.info(f"==========Augmentation Methods: {augment_file[i]}, with a strength value of {augment_strength[i]}==========")
            augment_file_path = f"Augmentation.{augment_file[i]}"
            _temp = __import__(name=augment_file_path, fromlist=['Aug'])
            Aug.append(_temp.Aug)
    
    
    #Aug[0]()    
    
    # Importing the model class
    logging.info(f"==========Model Selected: {model_file}==========")
    model_file_path = f"Model.{model_file}"
    _temp = __import__(name=model_file_path, fromlist=['ModelClass'])
    ModelClass = _temp.ModelClass
    
    # Importing the evaluation methods
    logging.info(f"==========Evaluation Method: {eval_file}==========")
    eval_file_path = f"Evaluation.{eval_file}"
    _temp = __import__(name=eval_file_path, fromlist=['Eval'])
    Eval = _temp.Eval    
    #Eval()
    
 
    # Creating the dataloaders
    labelledloader, unlabelledloader, validloader, testloader = Data_Load(task = task, batch_size = batch_size, seed = seed)
    logging.info("Dataloader ready")    
    
    
    # For supervised learning task
    if (task == "super"):
      torch.manual_seed(seed)

      train_tot_accs, valid_tot_accs = [], []
      train_tot_losses, valid_tot_losses = [], []

      Model = ModelClass(optimizer=optimizer,lr=learn_rate,weight_decay=weight_decay,momentum=momentum)
      Model = Model.to(device=device)

      for ep in range(epoch):

          # logging.info(f"==========Supervised Learning Epoch Number: {ep+1}/{epoch}==========")
          print(f"==========Supervised Learning Epoch Number: {ep+1}/{epoch}==========")
          train_accs, valid_accs = [], []
          train_losses, valid_losses = [], []

          for idx, batch in enumerate(labelledloader):
              data, target = batch
              data = data.to(device=device)
              labels = F.one_hot(target, num_classes = 10).float().to(device=device)

              batch_len = data.shape[0]
              aug_num = []

              if augment_file != None:

                for i in range(len(augment_strength)):
                  aug_num.append(augment_strength[i]*batch_len)

                if len(aug_num) != 1:
                  aug_num = torch.tensor(aug_num)
                  aug_ind = torch.cumsum(aug_num,0).int()
                else:
                  aug_ind = aug_num

                for i in range(len(Aug)):
                  if i == 0:
                    temp_Aug, temp_label = Aug[i](data[0:aug_ind[i]],labels[0:aug_ind[i]],torch.rand(1))
                    Aug_data = temp_Aug
                    Aug_labels = temp_label
                  else:
                    temp_Aug, temp_label = Aug[i](data[aug_ind[i-1]:aug_ind[i]],labels[aug_ind[i-1]:aug_ind[i]],torch.rand(1))
                    Aug_data = torch.cat((Aug_data, temp_Aug), 0)
                    Aug_labels = torch.cat((Aug_labels, temp_label), 0)

              else:
                Aug_data = torch.cat((data,data,data,data),0)
                Aug_labels = torch.cat((labels,labels,labels,labels),0)

              acc, loss = Model.train_sup_up(Aug_data,Aug_labels)
              train_accs.append(acc)
              train_losses.append(loss)

          train_tot_accs.append(sum(train_accs)/len(train_accs))
          train_tot_losses.append(sum(train_losses)/len(train_losses))

          # logging.info(f"==========Training Accuracy: {train_tot_accs[-1]:.3f} , Training Loss: {train_tot_losses[-1]:.3f}==========")    
          print(f"==========Training Accuracy: {train_tot_accs[-1]:.3f} , Training Loss: {train_tot_losses[-1]:.3f}==========")

          for idx, batch in enumerate(validloader):
              data, target = batch
              data = data.to(device=device)
              labels = F.one_hot(target, num_classes = 10).float().to(device=device)
              acc, loss = Model.evaluation(data,labels)
              valid_accs.append(acc)
              valid_losses.append(loss)

          valid_tot_accs.append(sum(valid_accs)/len(valid_accs))
          valid_tot_losses.append(sum(valid_losses)/len(valid_losses))

          # logging.info(f"==========Validation Accuracy: {valid_tot_accs[-1]:.3f} , Validation Loss: {valid_tot_losses[-1]:.3f}==========")    
          print(f"==========Validation Accuracy: {valid_tot_accs[-1]:.3f} , Validation Loss: {valid_tot_losses[-1]:.3f}==========")
    
    
    # For semi-supervised learning task
    elif (task == "semi"):
        
        # Training the labeller
        lab_train_tot_accs, lab_valid_tot_accs = [], []
        lab_train_tot_losses, lab_valid_tot_losses = [], []
        
        Labeller = ModelClass(config)
        
        for ep in range(epoch):
                  
            logging.info(f"==========Semi-supervised Learning Labeller Epoch Number: {ep+1}/epoch==========")
            train_accs, valid_accs = [], []
            train_losses, valid_losses = [], []
            
            for idx, batch in enumerate(labelledloader):
                data, target = batch
                acc, loss = Labeller.Train(data,target)
                train_accs.append(acc)
                train_losses.append(loss)
            
            lab_train_tot_accs.append(sum(train_accs)/len(train_accs))
            lab_train_tot_losses.append(sum(train_losses)/len(train_losses))
                
            logging.info(f"==========Training Accuracy: {lab_train_tot_accs[-1]:.3f} , Training Loss: {lab_train_tot_losses[-1]:.3f}==========")    
            
            for idx, batch in enumerate(validloader):
                data, target = batch
                acc, loss = Labeller.Evaluate(data,target)
                valid_accs.append(acc)
                valid_losses.append(loss)
                
            lab_valid_tot_accs.append(sum(valid_accs)/len(valid_accs))
            lab_valid_tot_losses.append(sum(valid_losses)/len(valid_losses))
            
            logging.info(f"==========Validation Accuracy: {lab_valid_tot_accs[-1]:.3f} , Validation Loss: {lab_valid_tot_losses[-1]:.3f}==========")          
        
                
        # Accuracy and loss when predicting the unlabelled data
        lab_accs = []
        lab_losses = []
        
        for idx, batch in enumerate(unlabelledloader):
            data, target = batch
            acc, loss = Labeller.Evaluate(data,target)
            lab_accs.append(acc)
            lab_losses.append(loss)
                
        lab_tot_accs = (sum(lab_accs)/len(lab_accs))
        lab_tot_losses = (sum(lab_losses)/len(lab_losses))
                    
        logging.info(f"==========Labelled Accuracy: {lab_tot_accs:.3f} , Labelled Loss: {lab_tot_losses:.3f}==========")           

       
        # Train the final model with labelled data and unlabelled data where the target is predicted by the the labeller
        train_tot_accs, valid_tot_accs = [], []
        train_tot_losses, valid_tot_losses = [], []
    
        Model = ModelClass(config)
        
        for ep in range(epoch):
            
                      
            logging.info(f"==========Semi-supervised Learning Model Epoch Number: {ep+1}/epoch==========")
            train_accs, valid_accs = [], []
            train_losses, valid_losses = [], []
            
            for idx, batch in enumerate(labelledloader):
                data, target = batch
                acc, loss = Model.Train(data,target)
                train_accs.append(acc)
                train_losses.append(loss)

            for idx, batch in enumerate(unlabelledloader):
                data, _ = batch
                acc, loss = Model.Train(data,Labeller.forward(data))
                train_accs.append(acc)
                train_losses.append(loss)
            
            train_tot_accs.append(sum(train_accs)/len(train_accs))
            train_tot_losses.append(sum(train_losses)/len(train_losses))
                
            logging.info(f"==========Training Accuracy: {train_tot_accs[-1]:.3f} , Training Loss: {train_tot_losses[-1]:.3f}==========")    
            
            for idx, batch in enumerate(validloader):
                data, target = batch
                acc, loss = Model.Evaluate(data,target)
                valid_accs.append(acc)
                valid_losses.append(loss)
                
            valid_tot_accs.append(sum(valid_accs)/len(valid_accs))
            valid_tot_losses.append(sum(valid_losses)/len(valid_losses))
            
            logging.info(f"==========Validation Accuracy: {valid_tot_accs[-1]:.3f} , Validation Loss: {valid_tot_losses[-1]:.3f}==========")          
        
        
        
        
    # For few-shot learning task
    else:    
    
    
    
    
    # Save model
    pickle_path = f"./Model/{args.config_file}.pickle"
    logging.info("Saving model to pickle file")
    with open(pickle_path, "wb") as f:
      pickle.dump(Model, f, pickle.HIGHEST_PROTOCOL)
    
    
    # Final test accuracy
    test_accs = []
    test_losses = []
    
    for idx, batch in enumerate(testloader):
        data, target = batch
        acc, loss = Model.Evaluate(data,target)
        test_accs.append(acc)
        test_losses.append(loss)
            
    test_tot_accs = (sum(test_accs)/len(test_accs))
    test_tot_losses = (sum(test_losses)/len(test_losses))
                
    logging.info(f"==========Test Accuracy: {test_tot_accs:.3f} , Test Loss: {test_tot_losses:.3f}==========")    
    
    
    #Evaluation method
    Eval(Model)
    
    
    return print("Experiment Complete")






if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IFT6759 Experiments")

    parser.add_argument(
        "-c",
        "--config",
        type = str,
        dest="config_file",
        help="(string) name of the configuration file located in ./Config",
        default = "Example.yaml"
    )
    
    parser.add_argument(
        "-d"
        "--device",
        type=str,
        choices=["cpu", "cuda"],
        default="cuda",
        dest="device",
        help="device to store tensors on (default: %(default)s).",
    )
    
    args = parser.parse_args()

    
    # Check for the device
    if (args.device == "cuda") and not torch.cuda.is_available():
        logging.warning(
            "CUDA is not available, make that your environment is running on GPU (e.g. in the Notebook Settings in Google Colab). "
            'Forcing device="cpu".'
        )
        args.device = "cpu"

    else:
        logging.warning(
            "You are about to run on CPU, and might run out of memory shortly. You can try setting batch_size=1 to reduce memory usage."
        )


    logs = main(args)






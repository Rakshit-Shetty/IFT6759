"""
Apply rotation in the range of [-180, 180].

    Args:
        data [Tensor]: input images with a size of [Batch size, Channel, Height, Width]
        seed [int]: seed for randomization; default: "6759" 

    Returns:
        aug_data [Tensor]: output images with a size of [4*Batch size, Channel, Height, Width], where the first [Batch size, Channel, Height, Width] is the original data

"""

import torch
import torchvision
import torchvision.transforms.functional as F

def Aug(data,labels):
    
    #torch.manual_seed(seed)
    aug_data = data
    
    for i in range(1):        
            aug_data = torch.cat((aug_data,F.affine(data,translate=[0,0],angle=torch.randint(-180, 180,(1,)).item(),scale=1,shear=0)))

    aug_labels = torch.cat((labels,labels))
    
    return aug_data,aug_labels
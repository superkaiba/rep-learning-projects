'''
Code completed from template given as part of Representation Learning class at MILA in Winter 2022
'''
import os
import random

import numpy as np
import torch
import h5py
from torch.utils.data import Dataset, DataLoader
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
class BassetDataset(Dataset):
    """
    BassetDataset class taken with permission from Dr. Ahmad Pesaranghader

    We have already processed the data in HDF5 format: er.h5
    See https://www.h5py.org/ for details of the Python package used

    We used the same data processing pipeline as the paper.
    You can find the code here: https://github.com/davek44/Basset
    """

    # Initializes the BassetDataset
    def __init__(self, path='./data/', f5name='er.h5', split='train', transform=None):
        """
        Args:
            :param path: path to HDF5 file
            :param f5name: HDF5 file name
            :param split: split that we are interested to work with
            :param transform (callable, optional): Optional transform to be applied on a sample
        """
        self.split = split

        split_dict = {'train': ['train_in', 'train_out'],
                      'test': ['test_in', 'test_out'],
                      'valid': ['valid_in', 'valid_out']}

        assert self.split in split_dict, "'split' argument can be only defined as 'train', 'valid' or 'test'"

        # Open hdf5 file where one-hoted data are stored
        self.dataset = h5py.File(os.path.join(path, f5name.format(self.split)), 'r')

        # Keeping track of the names of the target labels
        self.target_labels = self.dataset['target_labels']

        # Get the list of volumes
        self.inputs = self.dataset[split_dict[split][0]]
        self.outputs = self.dataset[split_dict[split][1]]

        self.ids = list(range(len(self.inputs)))
        if self.split == 'test':
            self.id_vars = np.char.decode(self.dataset['test_headers'])

    def __getitem__(self, i):
        """
        Returns the sequence and the target at index i

        Notes:
        * The data is stored as float16, however, your model will expect float32.
          Do the type conversion here!
        * Pay attention to the output shape of the data.
          Change it to match what the model is expecting
          hint: https://pytorch.org/docs/stable/generated/torch.nn.Conv2d.html
        * The target must also be converted to float32
        * When in doubt, look at the output of __getitem__ !
        """

        idx = self.ids[i]
        # Sequence & Target
        output = {'sequence': torch.transpose(torch.transpose(torch.tensor(self.inputs[i]), 0, 1), 1, 2).type(torch.float32), 'target': torch.tensor(self.outputs[i]).type(torch.float32)}

        return output

    def __len__(self):
        return len(self.inputs)

    def get_seq_len(self):
        """
        Answer to Q1 part 2.
        Returns length of sequences for input data
        """
        return 600

    def is_equivalent(self):
        """
        Answer to Q1 part 3
        """
        return True


class Basset(nn.Module):
    """
    Basset model
    Architecture specifications can be found in the supplementary material
    You will also need to use some Convolution Arithmetic
    """

    def __init__(self):
        super(Basset, self).__init__()

        self.dropout = 0.3  # should be float
        self.num_cell_types = 164

        self.conv1 = nn.Conv2d(1, 300, (19, 4), stride=(1, 1), padding=(9, 0)) 
        self.conv2 = nn.Conv2d(300, 200, (11, 1), stride=(1, 1), padding=(5, 0)) 
        self.conv3 = nn.Conv2d(200, 200, (7, 1), stride=(1, 1), padding=(4, 0))

        self.bn1 = nn.BatchNorm2d(300)
        self.bn2 = nn.BatchNorm2d(200)
        self.bn3 = nn.BatchNorm2d(200)
        self.maxpool1 = nn.MaxPool2d((3, 1))
        self.maxpool2 = nn.MaxPool2d((4, 1))
        self.maxpool3 = nn.MaxPool2d((4, 1))

        self.fc1 = nn.Linear(13*200, 1000)
        self.bn4 = nn.BatchNorm1d(1000)

        self.fc2 = nn.Linear(1000, 1000)
        self.bn5 = nn.BatchNorm1d(1000)

        self.fc3 = nn.Linear(1000, self.num_cell_types)

    def forward(self, x):
        """
        Compute forward pass for the model.
        nn.Module will automatically create the `.backward` method!

        Note:
            * You will have to use torch's functional interface to 
              complete the forward method as it appears in the supplementary material
            * There are additional batch norm layers defined in `__init__`
              which you will want to use on your fully connected layers
            * Don't include the output activation here!
        """
        y = self.maxpool1(F.relu(self.bn1(self.conv1(x))))
        y = self.maxpool2(F.relu(self.bn2(self.conv2(y))))
        y = self.maxpool3(F.relu(self.bn3(self.conv3(y))))
        y = y.view(-1, 200 * 13)
        y = F.dropout(F.relu(self.bn4(self.fc1(y))), p=self.dropout, training=self.training)
        y = F.dropout(F.relu(self.bn5(self.fc2(y))), p=self.dropout, training=self.training)
        return self.fc3(y)


def compute_fpr_tpr(y_true, y_pred):
    """
    Computes the False Positive Rate and True Positive Rate
    Args:
        :param y_true: groundtruth labels (np.array of ints [0 or 1])
        :param y_pred: model decisions (np.array of ints [0 or 1])

    :Return: dict with keys 'tpr', 'fpr'.
             values are floats
    """
    output = {'fpr': 0., 'tpr': 0.}

    num_pos = np.count_nonzero(y_true)
    num_neg = len(y_true) - num_pos
    num_corr_pos = np.count_nonzero(y_true * y_pred)
    num_incorr_pos = np.count_nonzero(y_pred > y_true)

    output['tpr'] = num_corr_pos/num_pos
    output['fpr'] = num_incorr_pos/num_neg
    return output


def compute_fpr_tpr_dumb_model():
    """
    Simulates a dumb model and computes the False Positive Rate and True Positive Rate

    :Return: dict with keys 'tpr_list', 'fpr_list'.
             These lists contain the tpr and fpr for different thresholds (k)
             fpr and tpr values in the lists should be floats
             Order the lists such that:
                 output['fpr_list'][0] corresponds to k=0.
                 output['fpr_list'][1] corresponds to k=0.05
                 ...
                 output['fpr_list'][-1] corresponds to k=0.95

            Do the same for output['tpr_list']

    """
    output = {'fpr_list': [], 'tpr_list': []}

    binary_random = np.random.binomial(n=1, p=0.5, size=1000)
    uniform_random = np.random.uniform(size=1000)

    k_list = [0.05 * i for i in range(20)]
    for k in k_list:
      model_predictions = (uniform_random > k)

      output_k = compute_fpr_tpr(binary_random, model_predictions)

      output['fpr_list'].append(output_k['fpr'])
      output['tpr_list'].append(output_k['tpr'])
    
    return output


def compute_fpr_tpr_smart_model():
    """
    Simulates a smart model and computes the False Positive Rate and True Positive Rate

    :Return: dict with keys 'tpr_list', 'fpr_list'.
             These lists contain the tpr and fpr for different thresholds (k)
             fpr and tpr values in the lists should be floats
             Order the lists such that:
                 output['fpr_list'][0] corresponds to k=0.
                 output['fpr_list'][1] corresponds to k=0.05
                 ...
                 output['fpr_list'][-1] corresponds to k=0.95

            Do the same for output['tpr_list']
    """
    output = {'fpr_list': [], 'tpr_list': []}

    true_outputs = np.random.binomial(n=1, p=0.5, size=1000)
    model_outputs = np.zeros(1000)

    for i in range(len(true_outputs)):
      if true_outputs[i] == 0:
        model_outputs[i] = np.random.uniform(low=0, high=0.6)
      else:
        model_outputs[i] = np.random.uniform(low=0.4, high=1)

    k_list = [0.05 * i for i in range(20)]
    for k in k_list:
      model_predictions = (model_outputs > k)
      
      output_k = compute_fpr_tpr(true_outputs, model_predictions)

      output['fpr_list'].append(output_k['fpr'])
      output['tpr_list'].append(output_k['tpr'])

    return output


def compute_auc_both_models():
    """
    Simulates a dumb model and a smart model and computes the AUC of both

    :Return: dict with keys 'auc_dumb_model', 'auc_smart_model'.
             These contain the AUC for both models
             auc values in the lists should be floats
    """
    output = {'auc_dumb_model': 0., 'auc_smart_model': 0.}

    true_outputs = np.random.binomial(n=1, p=0.5, size=1000)
    dumb_outputs = np.random.uniform(size=1000)
    smart_outputs = np.zeros(1000)

    for i in range(len(true_outputs)):
      if true_outputs[i] == 0:
        smart_outputs[i] = np.random.uniform(low=0, high=0.6)
      else:
        smart_outputs[i] = np.random.uniform(low=0.4, high=1)

    output['auc_dumb_model'] = compute_auc(true_outputs, dumb_outputs)['auc']
    output['auc_smart_model'] = compute_auc(true_outputs, smart_outputs)['auc']

    return output


def compute_auc_untrained_model(model, dataloader, device):
    """
    Computes the AUC of your input model

    Args:
        :param model: solution.Basset()
        :param dataloader: torch.utils.data.DataLoader
                           Where the dataset is solution.BassetDataset
        :param device: torch.device

    :Return: dict with key 'auc'.
             This contains the AUC for the model
             auc value should be float

    Notes:
    * Dont forget to re-apply your output activation!
    * Make sure this function works with arbitrarily small dataset sizes!
    * You should collect all the targets and model outputs and then compute AUC at the end
      (compute time should not be as much of a consideration here)
    """
    model.training = False
    model.eval()
    model.train(False)
    output = {'auc': 0.}

    sig = nn.Sigmoid()
    y_list = []
    target_list = []
    for i, data in enumerate(dataloader):
      sequence, target = data['sequence'].to(device), data['target'].to(device)

      with torch.no_grad():
        y = sig(model.forward(sequence))

      y = y.cpu().detach().numpy().reshape(-1)
      target = target.cpu().detach().numpy().reshape(-1)
      y_list.append(y)
      target_list.append(target)

    y_list = np.concatenate(y_list)
    target_list = np.concatenate(target_list)
    output['auc'] = compute_auc(target_list, y_list)['auc']

    return output


def compute_auc(y_true, y_model):
    """
    Computes area under the ROC curve (using method described in main.ipynb)
    Args:
        :param y_true: groundtruth labels (np.array of ints [0 or 1])
        :param y_model: model outputs (np.array of float32 in [0, 1])
    :Return: dict with key 'auc'.
             This contains the AUC for the model
             auc value should be float

    Note: if you set y_model as the output of solution.Basset, 
    you need to transform it before passing it here!
    """
    output = {'auc': 0.}
    fpr_tpr_list = []
    k_list = np.arange(0, 1, 0.05)
    for k in k_list:
      model_predictions = (y_model >= k)
      output_k = compute_fpr_tpr(y_true, model_predictions)
      fpr_tpr_list.append((output_k['fpr'], output_k['tpr']))

    fpr_tpr_list.sort(key=lambda x:x[0])
    x = [i[0] for i in fpr_tpr_list]
    y = [i[1] for i in fpr_tpr_list]
    output['auc'] = np.trapz(y, x=x)

    return output


def get_critereon():
    """
    Picks the appropriate loss function for our task
    criterion should be subclass of torch.nn
    """

    return nn.BCEWithLogitsLoss()


def train_loop(model, train_dataloader, device, optimizer, criterion):
    """
    One Iteration across the training set
    Args:
        :param model: solution.Basset()
        :param train_dataloader: torch.utils.data.DataLoader
                                 Where the dataset is solution.BassetDataset
        :param device: torch.device
        :param optimizer: torch.optim
        :param critereon: torch.nn (output of get_critereon)

    :Return: total_score, total_loss.
             float of model score (AUC) and float of model loss for the entire loop (epoch)
             (if you want to display losses and/or scores within the loop, 
             you may print them to screen)

    Make sure your loop works with arbitrarily small dataset sizes!

    Note: you don’t need to compute the score after each training iteration.
    If you do this, your training loop will be really slow!
    You should instead compute it every 50 or so iterations and aggregate ...
    """
    model.train()
    model.training = True
    model.to(device)
    output = {'total_score': 0.,
              'total_loss': 0.}

    criterion = get_critereon()
    current_ys = []
    current_targets = []
    curr_total_loss = 0
    curr_total_score = 0
    print(len(train_dataloader))
    sig = nn.Sigmoid()
    for i, data in enumerate(train_dataloader):
      #print(i)
      sequence, target = data['sequence'].to(device), data['target'].to(device)
      y = model.forward(sequence)
      loss = criterion(y, target)

      optimizer.zero_grad()
      loss.backward()
      optimizer.step()
      output["total_loss"] += loss
      curr_total_loss += loss
      with torch.no_grad():
        y = sig(y).cpu().detach().numpy().reshape(-1)
      target = target.cpu().detach().numpy().reshape(-1)


      current_ys.append(y)
      current_targets.append(target)
      if i != 0 and i % 50 == 0:
        ys = np.concatenate(current_ys)
        targets = np.concatenate(current_targets)
        score = compute_auc(targets, ys)
        curr_total_score += score['auc']
        current_ys = []
        current_targets = []
        output["total_score"] += score['auc']
      if i % 500 == 0:
        print("Training Score: ", curr_total_score/10)
        print("Training Loss: ", curr_total_loss.item())
        curr_total_loss = 0
        curr_total_score = 0

    print(output)
    return output['total_score'], output['total_loss']


def valid_loop(model, valid_dataloader, device, optimizer, criterion):
    """
    One Iteration across the validation set
    Args:
        :param model: solution.Basset()
        :param valid_dataloader: torch.utils.data.DataLoader
                                 Where the dataset is solution.BassetDataset
        :param device: torch.device
        :param optimizer: torch.optim
        :param critereon: torch.nn (output of get_critereon)

    :Return: total_score, total_loss.
             float of model score (AUC) and float of model loss for the entire loop (epoch)
             (if you want to display losses and/or scores within the loop, 
             you may print them to screen)

    Make sure your loop works with arbitrarily small dataset sizes!
    
    Note: if it is taking very long to run, 
    you may do simplifications like with the train_loop.
    """
    output = {'total_score': 0.,
              'total_loss': 0.}
    sig = nn.Sigmoid()
    with torch.no_grad():
      model.eval()
      model.to(device)
      model.training = False

      criterion = get_critereon()

      for i, data in enumerate(valid_dataloader):
        sequence, target = data['sequence'].to(device), data['target'].to(device)

        y = model.forward(sequence)
        loss = criterion(y, target)
        output["total_loss"] += loss
        #print("Loss: ", loss)
        
        y = sig(y).cpu().detach().numpy().reshape(-1)
        target = target.cpu().detach().numpy().reshape(-1)

        score = compute_auc(target, y)
        output["total_score"] += score['auc']
    output["total_score"] = output["total_score"]/len(valid_dataloader)
    output["total_loss"] = output["total_loss"]/len(valid_dataloader)

    return output['total_score'], output['total_loss']


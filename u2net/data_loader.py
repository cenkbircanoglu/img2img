from __future__ import print_function, division

import glob
import os
import random
from math import ceil

import numpy as np
import pandas as pd
import torch
from skimage import io, transform, color
from torch.utils.data import Dataset
from torch.utils.data.dataloader import DataLoader
from torchvision.transforms import transforms
from tqdm import tqdm


class RescaleT(object):

    def __init__(self, output_size):
        assert isinstance(output_size, (int, tuple))
        self.output_size = output_size

    def __call__(self, sample):
        imidx, image, label = sample['imidx'], sample['image'], sample['label']

        # #resize the image to new_h x new_w and convert image from range [0,255] to [0,1]
        # img = transform.resize(image,(new_h,new_w),mode='constant')
        # lbl = transform.resize(label,(new_h,new_w),mode='constant', order=0, preserve_range=True)

        img = transform.resize(image, (self.output_size, self.output_size), mode='constant')
        lbl = transform.resize(label, (self.output_size, self.output_size), mode='constant')

        return {'imidx': imidx, 'image': img, 'label': lbl}


class Rescale(object):

    def __init__(self, output_size):
        assert isinstance(output_size, (int, tuple))
        self.output_size = output_size

    def __call__(self, sample):
        imidx, image, label = sample['imidx'], sample['image'], sample['label']

        if random.random() >= 0.5:
            image = image[::-1]
            label = label[::-1]

        h, w = image.shape[:2]

        if isinstance(self.output_size, int):
            if h > w:
                new_h, new_w = self.output_size * h / w, self.output_size
            else:
                new_h, new_w = self.output_size, self.output_size * w / h
        else:
            new_h, new_w = self.output_size

        new_h, new_w = int(new_h), int(new_w)

        # #resize the image to new_h x new_w and convert image from range [0,255] to [0,1]
        img = transform.resize(image, (new_h, new_w), mode='constant')
        lbl = transform.resize(label, (new_h, new_w), mode='constant')

        return {'imidx': imidx, 'image': img, 'label': lbl}


class RandomCrop(object):

    def __init__(self, output_size):
        assert isinstance(output_size, (int, tuple))
        if isinstance(output_size, int):
            self.output_size = (output_size, output_size)
        else:
            assert len(output_size) == 2
            self.output_size = output_size

    def __call__(self, sample):
        imidx, image, label = sample['imidx'], sample['image'], sample['label']

        if random.random() >= 0.5:
            image = image[::-1]
            label = label[::-1]

        h, w = image.shape[:2]
        new_h, new_w = self.output_size

        top = np.random.randint(0, h - new_h)
        left = np.random.randint(0, w - new_w)

        image = image[top: top + new_h, left: left + new_w]
        label = label[top: top + new_h, left: left + new_w]

        return {'imidx': imidx, 'image': image, 'label': label}


class ToTensorLab(object):
    """Convert ndarrays in sample to Tensors."""

    def __init__(self, flag=0):
        self.flag = flag

    def __call__(self, sample):
        imidx, image, label = sample['imidx'], sample['image'], sample['label']

        # if (np.max(label) < 1e-6):
        #     label = label
        # else:
        #     label = label / np.max(label)
        #
        # tmpImg = np.zeros((image.shape[0], image.shape[1], 3))
        # image = image / np.max(image)
        # if image.shape[2] == 1:
        #     tmpImg[:, :, 0] = (image[:, :, 0] - 0.485) / 0.229
        #     tmpImg[:, :, 1] = (image[:, :, 0] - 0.485) / 0.229
        #     tmpImg[:, :, 2] = (image[:, :, 0] - 0.485) / 0.229
        # else:
        #     tmpImg[:, :, 0] = (image[:, :, 0] - 0.485) / 0.229
        #     tmpImg[:, :, 1] = (image[:, :, 1] - 0.456) / 0.224
        #     tmpImg[:, :, 2] = (image[:, :, 2] - 0.406) / 0.225
        #
        # tmpLbl = np.zeros((label.shape[0], label.shape[1], 3))
        # label = label / np.max(label)
        # if label.shape[2] == 1:
        #     tmpLbl[:, :, 0] = (label[:, :, 0] - 0.485) / 0.229
        #     tmpLbl[:, :, 1] = (label[:, :, 0] - 0.485) / 0.229
        #     tmpLbl[:, :, 2] = (label[:, :, 0] - 0.485) / 0.229
        # else:
        #     tmpLbl[:, :, 0] = (label[:, :, 0] - 0.485) / 0.229
        #     tmpLbl[:, :, 1] = (label[:, :, 1] - 0.456) / 0.224
        #     tmpLbl[:, :, 2] = (label[:, :, 2] - 0.406) / 0.225

        # change the r,g,b to b,r,g from [0,255] to [0,1]
        # transforms.Normalize(mean = (0.485, 0.456, 0.406), std = (0.229, 0.224, 0.225))
        tmpImg = image.transpose((2, 0, 1)).copy()
        tmpLbl = label.transpose((2, 0, 1)).copy()
        return {'imidx': torch.from_numpy(imidx), 'image': torch.from_numpy(tmpImg), 'label': torch.from_numpy(tmpLbl)}


class SalObjDataset(Dataset):
    def __init__(self, data_root, image_name_csv_file=None, img_folder_name='composite', mask_folder_name='masks',
                 name_field='ImageId', transform=None):
        self.label_name_list = []
        if image_name_csv_file:
            image_list = pd.read_csv(image_name_csv_file)[name_field].tolist()
            self.image_name_list = [os.path.join(data_root, img_folder_name, i) for i in image_list]
            label_folder = os.path.join(data_root, mask_folder_name)
            if os.path.exists(label_folder) and len(os.listdir(label_folder)) > 0:
                self.label_name_list = [os.path.join(label_folder, i) for i in image_list]

            del image_list
        else:
            jpg_folder = os.path.join(data_root, img_folder_name, '*.jpg')
            png_folder = os.path.join(data_root, img_folder_name, '*.png')
            self.image_name_list = glob.glob(jpg_folder) + glob.glob(png_folder)

            label_folder = os.path.join(data_root, mask_folder_name)
            if os.path.exists(label_folder) and len(os.listdir(label_folder)) > 0:
                for img_path in self.image_name_list:
                    img_name = img_path.split(os.sep)[-1]

                    aaa = img_name.split(".")
                    bbb = aaa[0:-1]
                    imidx = bbb[0]
                    for i in range(1, len(bbb)):
                        imidx = imidx + "." + bbb[i]

                    self.label_name_list.append(data_root + '/%s/%s%s' % (mask_folder_name, imidx, '.jpg'))
            else:
                print('There is no mask file in the folder')
        self.transform = transform

    def __len__(self):
        return len(self.image_name_list)

    def __getitem__(self, idx):
        try:
            image = io.imread(self.image_name_list[idx])
            imidx = np.array([idx])

            if image.shape[2] > 3:
                image = color.rgba2rgb(image)
            label = io.imread(self.label_name_list[idx])
            if label.shape[2] > 3:
                label = color.rgba2rgb(label)

            sample = {'imidx': imidx, 'image': image, 'label': label}

            if self.transform:
                sample = self.transform(sample)

            return sample
        except Exception as e:
            try:
                print(e, self.image_name_list[idx])
                try:
                    os.remove(self.image_name_list[idx])
                except:
                    pass
                try:
                    os.remove(self.label_name_list[idx])
                except:
                    pass
            except Exception as ee:
                print(ee)
            return self.__getitem__(idx + 1)


if __name__ == '__main__':
    selected_image_sizes = [284]
    for selected_image_size in selected_image_sizes:
        dataset = SalObjDataset('./datasets/vide_dressing/', transform=transforms.Compose([
            RescaleT(selected_image_size),
            RandomCrop(ceil(selected_image_size - (selected_image_size / 10))),
            ToTensorLab(flag=0)]))
        loader = DataLoader(dataset, num_workers=32, shuffle=False)
        for i in tqdm(loader, total=len(loader.dataset)):
            print(i)

import torch
from abc import ABCMeta, abstractmethod
from random import randint
import numpy as np
import cv2
from torchvision.transforms import transforms


class Augmentation(metaclass=ABCMeta):
    def __init__(self, config: {}, aug_name: str):
        self.__aug_name = aug_name
        self._percentage = self._get_config_path(config)['percentage']

    def __call__(self, data):
        """
        Process data
        :param data: data object
        :return: processed data object
        """
        if randint(1, 100) <= self._percentage:
            return self.process(data)
        else:
            return data

    @abstractmethod
    def process(self, data):
        """
        Process data
        :param data: data object
        :return: processed data object
        """

    def _get_config_path(self, config):
        return config[self.__aug_name]

    def get_percetage(self):
        return self._percentage

    def get_name(self):
        return self.__aug_name

    @abstractmethod
    def _get_config(self) -> {}:
        """
        Internal method for getting config
        :return: internal config dict
        """

    def get_config(self) -> {}:
        """
        Get current config
        :return: config dict
        """
        internal_config = {"percentage": self.get_percetage()}
        internal_config.update(self._get_config())
        return {self.get_name(): internal_config}


class HorizontalFlip(Augmentation):
    def __init__(self, config: {}):
        super().__init__(config, 'hflip')

    def process(self, data):
        return cv2.flip(data.copy(), 1)

    def _get_config(self) -> {}:
        return {}


class VerticalFlip(Augmentation):
    def __init__(self, config: {}):
        super().__init__(config, 'vflip')

    def process(self, data):
        return cv2.flip(data.copy(), 0)

    def _get_config(self) -> {}:
        return {}


class GaussNoise(Augmentation):
    def __init__(self, config: {}):
        super().__init__(config, 'gauss_noise')

        self.__mean = self._get_config_path(config)['mean']
        self.__var = self._get_config_path(config)['var']
        self.__interval = self._get_config_path(config)['interval']

    def process(self, data):
        row, col, ch = data.shape
        sigma = self.__var ** 0.5
        gauss = np.random.normal(self.__mean, sigma, (row, col, ch))
        gauss = (gauss - np.min(gauss))
        gauss = gauss / np.max(gauss) * self.__interval
        return np.where((255 - data) < gauss, 255, data + gauss).astype(np.uint8)

    def _get_config(self) -> {}:
        return {'mean': self.__mean, 'var': self.__var, 'interval': self.__interval}


class SNPNoise(Augmentation):
    def __init__(self, config: {}):
        super().__init__(config, 'snp_noise')

        self.__s_vs_p = self._get_config_path(config)['s_vs_p']
        self.__amount = self._get_config_path(config)['amount']

    def process(self, data):
        out = data.copy()
        # Salt mode
        num_salt = np.ceil(self.__amount * data.size * self.__s_vs_p)
        coords = [np.random.randint(0, i - 1, int(num_salt))
                  for i in data.shape]
        out[coords] = 255

        # Pepper mode
        num_pepper = np.ceil(self.__amount * data.size * (1. - self.__s_vs_p))
        coords = [np.random.randint(0, i - 1, int(num_pepper))
                  for i in data.shape]
        out[coords] = 0
        return out

    def _get_config(self) -> {}:
        return {'s_vs_p': self.__s_vs_p, 'amount': self.__amount}


class Blur(Augmentation):
    def __init__(self, config: {}):
        super().__init__(config, 'blur')

        self.__ksize = self._get_config_path(config)['ksize']

    def process(self, data):
        return cv2.blur(data.copy(), (self.__ksize[0], self.__ksize[1])).astype(np.uint8)

    def _get_config(self) -> {}:
        return {'ksize': self.__ksize}


def resize_to_defined(data, size):
    return cv2.resize(data, (size[0], size[1]))


def resize_by_min_edge(data, size):
    min_size_idx = np.argmin(data.shape[0: 2])
    max_size_idx = 1 - min_size_idx
    max_size = size * data.shape[max_size_idx] // data.shape[min_size_idx]
    target_size = (size, max_size) if min_size_idx == 1 else (max_size, size)
    return cv2.resize(data, target_size)


class Resize(Augmentation):
    def __init__(self, config: {}):
        super().__init__(config, 'resize')
        self.__size = self._get_config_path(config)['size']
        self.__resize_fnc = resize_to_defined if type(self.__size) == list and len(
            self.__size) == 2 else resize_by_min_edge
        self._percentage = 100

    def process(self, data):
        return self.__resize_fnc(data, self.__size)

    def _get_config(self) -> {}:
        return {'size': self.__size}


class CentralCrop(Augmentation):
    def __init__(self, config: {}):
        super().__init__(config, 'ccrop')
        self.__size = self._get_config_path(config)['size']
        self.__width, self.__height = self.__size if type(self.__size) == list and len(self.__size) == 2 else [self.__size, self.__size]

    def process(self, data):
        h, w, c = data.shape
        dx, dy = (w - self.__width) // 2, (h - self.__height) // 2
        y1, y2 = dy, dy + self.__height
        x1, x2 = dx, dx + self.__width
        data = data[y1: y2, x1: x2, :]
        return data

    def _get_config(self) -> {}:
        return {'size': self.__size}


class RandomCrop(Augmentation):
    def __init__(self, config: {}):
        super().__init__(config, 'rcrop')
        self.__size = self._get_config_path(config)['size']
        self.__width, self.__height = self.__size if type(self.__size) == list and len(self.__size) == 2 else [self.__size, self.__size]

    def process(self, data):
        h, w, c = data.shape
        dx, dy = randint(0, w - self.__width) if w > self.__width else 0, \
                 randint(0, h - self.__height) if h > self.__height else 0
        y1, y2 = dy, dy + self.__height
        x1, x2 = dx, dx + self.__width
        data = data[y1: y2, x1: x2, :]
        return data

    def _get_config(self) -> {}:
        return {'size': self.__size}


class RandomRotate(Augmentation):
    def __init__(self, config: {}):
        super().__init__(config, 'rrotate')
        self.__interval = self._get_config_path(config)['interval']

    def process(self, data):
        rows, cols = data.shape[:2]
        angle = randint(self.__interval[0], self.__interval[1])

        if angle == 0:
            return data

        M = cv2.getRotationMatrix2D((cols / 2, rows / 2), angle, 1)
        img = cv2.warpAffine(data, M, (cols, rows))
        offset = abs(int(rows // (2 + 1 / np.tan(np.deg2rad(angle)))))
        return resize_to_defined(img[offset: rows - offset, offset: cols - offset], [rows, cols])

    def _get_config(self) -> {}:
        return {'interval': self.__interval}


class RandomBrightness(Augmentation):
    def __init__(self, config: {}):
        super().__init__(config, 'rbrightness')

        self.__interval = self._get_config_path(config)['interval']

    def process(self, data):
        brightness = randint(self.__interval[0], self.__interval[1])
        return np.where((255 - data) < brightness, 255, data + brightness)

    def _get_config(self) -> {}:
        return {'interval': self.__interval}


class RandomContrast(Augmentation):
    def __init__(self, config: {}):
        super().__init__(config, 'rcontrast')
        self.__interval = self._get_config_path(config)['interval']

    def process(self, data):
        contrast = randint(self.__interval[0], self.__interval[1]) / 100
        return np.where((data * contrast) > 255, 255, data * contrast).astype(np.uint8)

    def _get_config(self) -> {}:
        return {'interval': self.__interval}


class Normalize(Augmentation):
    def __init__(self, config: {}):
        super().__init__(config, 'normalize')
        self.__normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        self._percentage = 100

    def process(self, data):
        return self.__normalize(data)

    def _get_config(self) -> {}:
        return {}


class ToPyTorch(Augmentation):
    def __init__(self, config: {}):
        super().__init__(config, 'to_pytorch')
        self._percentage = 100

    def process(self, data):
        if data.dtype == np.uint8:
            return torch.from_numpy(np.moveaxis(data / 255., -1, 0).astype(np.float32))

        return torch.from_numpy(np.moveaxis(data, -1, 0).astype(np.float32))

    def _get_config(self) -> {}:
        return {}


augmentations_dict = {'hflip': HorizontalFlip,
                      'vflip': VerticalFlip,
                      'gauss_noise': GaussNoise,
                      'snp_noise': SNPNoise,
                      'blur': Blur,
                      'resize': Resize,
                      'ccrop': CentralCrop,
                      'rcrop': RandomCrop,
                      'rrotate': RandomRotate,
                      'to_pytorch': ToPyTorch,
                      'normalize': Normalize,
                      'rbrightness': RandomBrightness,
                      'rcontrast': RandomContrast}

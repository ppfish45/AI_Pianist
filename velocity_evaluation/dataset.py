import os
import cv2
import glob
import random
import numpy as np
import matplotlib.pyplot as plt

from ipywidgets import IntProgress
from IPython.display import display

if __name__ == "__main__":
    path = {
        'X_train': 'dataset/X_train',
        'X_test': 'dataset/X_test',
        'X_val': 'dataset/X_val',
        'y_train': 'dataset/y_train',
        'y_test': 'dataset/y_test',
        'y_val': 'dataset/y_val',
    }
else:
    path = {
        'X_train': 'dataset/X_train',
        'X_test': 'dataset/X_test',
        'X_val': 'dataset/X_val',
        'y_train': 'dataset/y_train',
        'y_test': 'dataset/y_test',
        'y_val': 'dataset/y_val',
    }
    '''
    path = {
        'X_train': 'keypress_recognition/dataset/X_train',
        'X_test': 'keypress_recognition/dataset/X_test',
        'X_val': 'keypress_recognition/dataset/X_val',
        'y_train': 'keypress_recognition/dataset/y_train',
        'y_test': 'keypress_recognition/dataset/y_test',
        'y_val': 'keypress_recognition/dataset/y_val',
    }
    '''
    
X_path = dict()
y_org = dict()

X = {
    'single': {
        'white': dict(),
        'black': dict()
    },
    'bundle': {
        'white': dict(),
        'black': dict()
    }
}
y = {
    'white': dict(),
    'black': dict()
}

X_series = {
    'train': {
        'white': [],
        'black': []
    },
    'test': {
        'white': [],
        'black': []
    },
    'val': {
        'white': [],
        'black': []
    }
}
y_series = {
    'train': {
        'white': [],
        'black': []
    },
    'test': {
        'white': [],
        'black': []
    },
    'val': {
        'white': [],
        'black': []
    }
}

# X['single']['white']['train']
# y['single']['white']['train']

black_mask = np.array(
    [1, 4, 6, 9, 11, 13, 16, 18, 21, 23, 25, 28, 30, 33, 35, 37, 40, 42, 45, 47, 49, 52, 54, 57, 59, 61, 64,
     66, 69, 71, 73, 76, 78, 81, 83, 85])
white_mask = np.array(
    [0, 2, 3, 5, 7, 8, 10, 12, 14, 15, 17, 19, 20, 22, 24, 26, 27, 29, 31, 32, 34, 36, 38, 39, 41, 43, 44, 46, 48,
     50, 51, 53, 55, 56, 58, 60, 62, 63, 65, 67, 68, 70, 72, 74, 75, 77, 79, 80, 82, 84, 86, 87])

def get_lstm_data_num(phase, color):
    return len(X_series[phase][color])

def load_all_data(
    spliter=['train', 'test', 'val'],
    color=['black', 'white'],
    size=['single', 'bundle'],
    keypress=True,
    difference=False,
    paddings=2
    ):
    for name in spliter:
        # X
        fp = os.path.join(path['X_' + name], '*.jpg')
        filelist = sorted(glob.glob(fp))
        X_path[name] = filelist
        # y
        fp = os.path.join(path['y_' + name], 'y_' + name + '.npy')
        y_org[name] = np.load(fp)
        y_org[name] = y_org[name][:, 21:109]
        # sanity check
        assert len(X_path[name]) == y_org[name].shape[0]
    if keypress:
        seperate(spliter, color, size)
    else:
        get_press_series(spliter, color, difference, paddings)

def pad_img(img, paddings):
    height, width, _ = img.shape # HWC
    padding = np.zeros([height, paddings, 3])
    _img = np.concatenate((padding, img, padding), axis=1).astype(np.uint8)
    del img
    return _img

def get_white_keys(keys, img, mask, paddings=0, one_key=None, need_pad=True):
    height, width, _ = img.shape # HWC
    if need_pad == False:
        width -= 2 * paddings
    unit_width = width // 52
    left = np.arange(52) * unit_width + paddings
    right = (np.arange(52) + 1) * unit_width + paddings
    # add paddings to original img
    if need_pad:
        padding = np.zeros([height, paddings, 3])
        img = np.concatenate((padding, img, padding), axis=1).astype(np.uint8)
    if keys == None:
        return img[:, left[one_key] - paddings : right[one_key] + paddings, :]
    else:
        for i in mask:
            keys.append(img[:, left[i] - paddings : right[i] + paddings, :])

def get_black_boundaries(img, expected_width=16):
    '''
    want a grayscale image, (h, w) format
    '''
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(img, (5, 5), 0)
    _, bw = cv2.threshold(blur, 127, 255, cv2.THRESH_OTSU)
    upper = np.mean(bw[0:5], axis=0)
    
    black_keys = []

    last = -1

    for i, x in enumerate(upper):
        if x <= 255 / 5:
            if last == -1:
                last = i
        else:
            if last != -1:
                black_keys.append([last, i - 1])
                last = -1

    for i, coor in enumerate(black_keys):
        x, y = coor
        offset = (expected_width - (y - x + 1)) // 2
        coor[0] = x - offset
        coor[1] = y + (expected_width - (y - x + 1) - offset)
    
    return np.array(black_keys)

def get_black_keys(keys, img, boundaries, mask, paddings=0, one_key=None, need_pad=True):
    height, width, _ = img.shape # HWC
    left = boundaries[:, 0] + paddings
    right = boundaries[:, 1] + paddings
    # add paddings to original img
    if need_pad:
        padding = np.zeros([height, paddings, 3])
        img = np.concatenate((padding, img, padding), axis=1).astype(np.uint8)
    if keys == None:
        return img[:, left[one_key] - paddings : right[one_key] + paddings + 1, :]
    else:
        for i in mask:
            keys.append(img[:, left[i] - paddings : right[i] + paddings + 1, :])

def get_masks(y_info, offset=2):
    white_tmp_mask = []
    black_tmp_mask = []
    for i, x in enumerate(white_mask):
        l = max(0, x - offset)
        r = min(87, x + offset)
        if np.max(y_info[l:r+1]) > 0:
            white_tmp_mask.append(i)
    for i, x in enumerate(black_mask):
        l = max(0, x - offset)
        r = min(87, x + offset)
        if np.max(y_info[l:r+1]) > 0:
            black_tmp_mask.append(i)
    return (white_tmp_mask, black_tmp_mask)

tmp_imgs = []

def add_series(spliter, color, start, end, key_index, paddings, black_coor=None, difference=False):
    offset = 2
    N = y_org[spliter].shape[0]
    index = None
    if color == 'black':
        index = np.where(black_mask == key_index)[0][0]
    else:
        index = np.where(white_mask == key_index)[0][0]
    y_return = y_org[spliter][start][key_index]
    X_return = []
    for i in range(max(0, start - offset), min(N, end + offset + 1)):
        img = tmp_imgs[i]
        if color == 'black':
            X_return.append(get_black_keys(None, img, black_coor, None, paddings, index, need_pad=False))
        else:
            X_return.append(get_white_keys(None, img, None, paddings, index, need_pad=False))
    if difference:
        for i in range(1, len(X_return)):
            X_return[i] = cv2.subtract(X_return[i], X_return[0])
        X_return = X_return[1:]
    X_series[spliter][color].append(np.array(X_return))
    y_series[spliter][color].append(y_return)

def get_press_series(spliter, color, difference, paddings=2):
    global tmp_imgs
    
    white_width = 17 + 2 * paddings
    black_width = 16 + 2 * paddings
    height = 106
    width = 884

    print('Start extracting keypress series ...')
    print(f'  White width: {white_width}px')
    print(f'  Black width: {black_width}px')
    print(f'  Height: {height}px')
    print('')

    for name in spliter:
        black_coor = None
        N = y_org[name].shape[0]
        for p in X_path[name]:
            img = cv2.imread(p)
            black_coor = get_black_boundaries(img)
            if len(black_coor) == 36:
                break
        y_trans = np.transpose(y_org[name], (1, 0))
        
        print('Pre-loading images ...')
        
        bar = IntProgress(max=N)
        display(bar)
        for i in range(N):
            img = pad_img(cv2.imread(X_path[name][i]), paddings)
            tmp_imgs.append(img)
            bar.value += 1
        bar.close()
        
        bar = IntProgress(max=88)
        display(bar)

        for k in range(88):
            if k in black_mask:
                col = 'black'
            else:
                col = 'white'
            if col not in color:
                continue
            _y = y_trans[k]
            _y = np.argwhere(_y > 0).flatten()
            if _y.shape[0] == 0:
                continue
            last = _y[0]
            _n = len(_y)
            for i in range(_n):
                if i % 32 == 0:
                    bar.description = f'{i}/{_n}'
                if i != 0 and _y[i] != _y[i - 1] + 1:
                    if col == 'black':
                        add_series(name, col, last, _y[i - 1], k, paddings, black_coor, difference)
                    else:
                        add_series(name, col, last, _y[i - 1], k, paddings, difference)
                    last = _y[i]
                if i == _n - 1 and last != -1:
                    if col == 'black':
                        add_series(name, col, last, _y[i], k, paddings, black_coor, difference)
                    else:
                        add_series(name, col, last, _y[i], k, paddings, difference)
            bar.value += 1

        bar.close()

        del tmp_imgs
        tmp_imgs = []

        print(f'{name} set loading finished ...')
        print('  Pressed white keys: ' + str(len(X_series[name]['white'])))
        print('  Pressed black keys: ' + str(len(X_series[name]['black'])))

def seperate(spliter, color, size):

    single_paddings = 2
    bundle_paddings = 10
    white_single_width = 17 + 2 * single_paddings
    white_bundle_width = 17 + 2 * bundle_paddings
    black_single_width = 16 + 2 * single_paddings
    black_bundle_width = 16 + 2 * bundle_paddings
    height = 106
    width = 884

    print('Start seperating keyboard ...')
    print(f'  White single width: {white_single_width}px')
    print(f'  Black single width: {black_single_width}px')
    print(f'  White bundle width: {white_bundle_width}px')
    print(f'  Black bundle width: {black_bundle_width}px')

    for name in spliter:
        black_coor = None
        for p in X_path[name]:
            img = cv2.imread(p)
            black_coor = get_black_boundaries(img)
            if len(black_coor) == 36:
                break
        X['single']['white'][name] = []
        X['single']['black'][name] = []
        X['bundle']['white'][name] = []
        X['bundle']['black'][name] = []
        y['white'][name] = []
        y['black'][name] = []

        bar = IntProgress(max=len(X_path[name]))
        display(bar)

        for i, p in enumerate(X_path[name]):
            white_tmp_mask = None
            black_tmp_mask = None
            if random.random() > 0.005:
                white_tmp_mask, black_tmp_mask = get_masks(y_org[name][i])
            else:
                white_tmp_mask = np.arange(52)
                black_tmp_mask = np.arange(36)
            img = cv2.imread(p)
            if 'single' in size:
                if 'white' in color:
                    get_white_keys(X['single']['white'][name], img, white_tmp_mask, paddings=single_paddings)
                if 'black' in color:
                    get_black_keys(X['single']['black'][name], img, black_coor, black_tmp_mask, paddings=single_paddings)
            if 'bundle' in size:
                if 'white' in color:
                    get_white_keys(X['bundle']['white'][name], img, white_tmp_mask, paddings=bundle_paddings)
                if 'black' in color:
                    get_black_keys(X['bundle']['black'][name], img, black_coor, black_tmp_mask, paddings=bundle_paddings)
            for ind in white_mask[white_tmp_mask]:
                y['white'][name].append(y_org[name][i][ind])
            for ind in black_mask[black_tmp_mask]:
                y['black'][name].append(y_org[name][i][ind])
            bar.value += 1
            del img
        bar.close()
        
        print('In ' + name + 'set: ')
        for kind in color:
            for k2 in size:
                X[k2][kind][name] = np.array(X[k2][kind][name])
            y[kind][name] = np.array(y[kind][name])
            print('  # of pressed ' + kind + ' key: ' + str(np.sum(y[kind][name] > 0)))
            print('  # of unpressed ' + kind + ' key: ' + str(np.sum(y[kind][name] <= 0)))

class lstm_data_batch:
    def __init__(
        self,
        type='train',
        color='white',
        NCHW=True,
        shuffle=True,
        need_bar=True,
        max_num=-1
    ):
        self.type = type
        self.color = color
        self.NCHW = NCHW
        self.need_bar = need_bar
        if max_num == -1:
            self.max_num = len(X_series[type][color])
        else:
            self.max_num = max_num
        self.order = np.arange(self.max_num)
        if shuffle:
            random.shuffle(self.order)
        if need_bar:
            self.bar = IntProgress(max=self.max_num)
            display(self.bar)

    def __iter__(self):
        self.index = 0
        return self

    def __next__(self):
        if self.index >= self.max_num:
            if self.need_bar:
                self.bar.close()
            raise StopIteration
        ind = self.order[self.index]
        X_return = X_series[self.type][self.color][ind]
        y_return = y_series[self.type][self.color][ind]
        if self.NCHW:
            X_return = np.transpose(X_return, (0, 3, 1, 2))
        self.index += 1
        if self.need_bar:
            self.bar.value += 1
        return (np.array(X_return), np.array(y_return))        

class data_batch:
    def __init__(
        self,
        type='train',
        size='single',
        color='white',
        batch_size=64,
        need_velocity=True,
        NCHW=True,
        shuffle=True,
        max_num=-1
    ):
        self.size = size
        self.type = type
        self.color = color
        self.batch_size = batch_size
        self.NCHW = NCHW
        self.max_num = max_num
        self.pressed = []
        self.unpressed = []
        self.num_pressed = 0
        self.num_unpressed = 0
        self.need_velocity = need_velocity
        for i, x in enumerate(y[color][type]):
            if x > 0:
                self.pressed.append(i)
                self.num_pressed += 1
            else:
                self.unpressed.append(i)
                self.num_unpressed += 1
        if shuffle:
            random.shuffle(self.pressed)
            random.shuffle(self.unpressed)
        if self.max_num == -1:
            self.max_num = len(self.unpressed)
            self.iter_num = len(self.unpressed) * 2
        else:
            self.max_num = self.max_num // 2
            self.iter_num = max_num
        self.bar = IntProgress(max=self.iter_num)
        display(self.bar)

    def __iter__(self):
        self.index = 0
        return self

    def __next__(self):
        start = self.index * self.batch_size // 2
        end = (self.index + 1) * self.batch_size // 2
        if start >= self.max_num:
            self.bar.close()
            raise StopIteration
        if end >= self.max_num:
            end = self.max_num
            start = end - self.batch_size // 2
        self.index += 1
        ind = np.array([])
        s = start % self.num_pressed
        t = end % self.num_pressed
        if start // self.num_pressed == end // self.num_pressed:
            ind = np.append(ind, np.array(self.pressed[s:t]))
        else:
            ind = np.append(ind, np.array(self.pressed[s:]))
            ind = np.append(ind, np.array(self.pressed[:t]))
        ind = np.append(ind, np.array(self.unpressed[start:end]))
        ind = ind.flatten().astype('int64')
        X_return = X[self.size][self.color][self.type][ind]
        if self.NCHW:
            X_return = np.transpose(X_return, (0, 3, 1, 2))
        y_return = y[self.color][self.type][ind]
        if not self.need_velocity:
            y_return = (y_return > 0).astype(np.int)
        self.bar.value += self.batch_size
        return (X_return, y_return)
import keras
from keras.models import model_from_json
from keras.models import Sequential
from keras.layers import Dense, Dropout, Flatten
from keras.layers import Conv2D, MaxPooling2D
from keras.layers.advanced_activations import LeakyReLU
from keras.preprocessing.image import ImageDataGenerator
from keras.callbacks import ModelCheckpoint
from keras.callbacks import EarlyStopping
from keras.callbacks import LearningRateScheduler
from keras.utils import to_categorical
from sklearn.model_selection import StratifiedShuffleSplit

import numpy as np
import gzip
import math
from math import floor
from skimage.transform import resize
import cv2
import os

def TENG(img):
    """Implements the Tenengrad (TENG) focus measure operator.
    Based on the gradient of the image.
    :param img: the image the measure is applied to
    :type img: numpy.ndarray
    :returns: numpy.float32 -- the degree of focus
    """
    gaussianX = cv2.Sobel(img, cv2.CV_64F, 1, 0)
    gaussianY = cv2.Sobel(img, cv2.CV_64F, 1, 0)
    return np.mean(gaussianX * gaussianX +
                      gaussianY * gaussianY)

def PreprocessImgs(imgs, target_size):
    new_imgs = np.ones((len(imgs), target_size[0], target_size[1]))

    for i in range(len(imgs)):
        current = imgs[i]
        majorside = np.amax(current.shape)
        majorside_idx = np.argmax(current.shape)
        minorside = np.amin(current.shape)

        factor = target_size[0]/majorside
        minorside_new = floor(minorside*factor)
        minorside_pad = floor((target_size[0] - minorside_new)/2)
        
        if majorside_idx == 0:
            current = resize(current, (target_size[0], minorside_new), mode='constant', anti_aliasing=True)
            for j in range(current.shape[0]):
                for k in range(current.shape[1]):
                    new_imgs[i,j,(k + minorside_pad)] = current[j,k]

        if majorside_idx == 1:
            current = resize(current, (minorside_new, target_size[1]), mode='constant', anti_aliasing=True)
            for j in range(current.shape[0]):
                for k in range(current.shape[1]):
                    new_imgs[i,(j + minorside_pad),k] = current [j,k]

        new_imgs[i] = new_imgs[i].astype('float32')

    
    return new_imgs

def LoadTrainData(target_shape):
    train_path = "../laps_nobg_100/images_train.npy.gz"
    labels_path = "../laps_nobg_100/labels_train.npy.gz"
    with gzip.open(labels_path, "rb") as f:
        labels = np.load(f)

    with gzip.open(train_path, "rb") as f:
        imgs = np.load(f)
    imgs = PreprocessImgs(imgs, (target_shape[0], target_shape[1]))

    focused_images = np.zeros((0,target_shape[0], target_shape[1]))
    focused_labels = np.zeros((0))

    for i in range(len(imgs)):
        focus_meas = TENG(imgs[i])
        focus_measure = np.log(focus_meas)
        if focus_measure > -3.3:
            img = np.reshape(imgs[i], (1, target_shape[0], target_shape[1]))
            focused_images = np.append(focused_images, img, axis=0)
            focused_labels = np.append(focused_labels, labels[i])

    new_shape = (len(focused_images), target_shape[0], target_shape[1], target_shape[2])
    focused_images = np.reshape(focused_images, new_shape)

    split = StratifiedShuffleSplit(n_splits=1,test_size=0.1)
    train_idx, valid_idx = next(split.split(np.zeros(len(focused_labels)), focused_labels))

    np.save("./train_indices_ftteste6.npy", train_idx)
    np.save("./valid_indices_ftteste6.npy", valid_idx)

    X_train, y_train = focused_images[train_idx], labels[train_idx]
    X_valid, y_valid = focused_images[valid_idx], labels[valid_idx]

    return X_train, y_train, X_valid, y_valid

def LoadModel(in_shape, num_classes):
    # FIXME: 
    # - In the original network, the bias for convolutional layers is set to 1.0
    model = Sequential()

    a = 0.3
    # This looks like they call l1 in the code
    model.add(Conv2D(32, (3,3), padding='same', input_shape=in_shape))
    model.add(LeakyReLU(alpha=a))
    model.add(Conv2D(16, (3,3), padding='same'))
    model.add(LeakyReLU(alpha=a))
    model.add(MaxPooling2D(pool_size=(3,3), strides=(2,2)))

    # This looks like what they call l2 in the code
    model.add(Conv2D(64, (3,3), padding='same'))
    model.add(LeakyReLU(alpha=a))
    model.add(Conv2D(32, (3,3), padding='same'))
    model.add(LeakyReLU(alpha=a))
    model.add(MaxPooling2D(pool_size=(3,3), strides=(2,2)))

    # This looks like what they cal l3 in the code
    model.add(Conv2D(128, (3,3), padding='same'))
    model.add(LeakyReLU(alpha=a))
    model.add(Conv2D(128, (3,3), padding='same'))
    model.add(LeakyReLU(alpha=a))
    model.add(Conv2D(64, (3,3), padding='same'))
    model.add(LeakyReLU(alpha=a))
    model.add(MaxPooling2D(pool_size=(3,3), strides=(2,2)))

    # This looks like what they call l4 in the code
    model.add(Conv2D(256, (3,3), padding='same'))
    model.add(LeakyReLU(alpha=a))
    model.add(Conv2D(256, (3,3), padding='same'))
    model.add(LeakyReLU(alpha=a))
    model.add(Conv2D(128, (3,3), padding='same'))
    model.add(LeakyReLU(alpha=a))
    model.add(MaxPooling2D(pool_size=(3,3), strides=(2,2)))
    model.add(Flatten())
    model.add(Dropout(0.5))

    # This looks like what they call l5
    model.add(Dense(256))
    model.add(LeakyReLU(alpha=a))
    model.add(Dropout(0.5))
    model.add(Dense(256))
    model.add(LeakyReLU(alpha=a))
    model.add(Dropout(0.5))

    return model

def step_decay(epoch):
        return 5e-3

batch_size = 32
num_classes= 20

img_shape = (95, 95, 1)

X_train, y_train, X_valid, y_valid = LoadTrainData(img_shape)

print(np.shape(y_train))
print(np.shape(y_valid))


X_train = X_train.astype("float32")
X_valid = X_valid.astype("float32")
y_train = to_categorical(y_train, num_classes)
y_valid = to_categorical(y_valid, num_classes)


datagen = ImageDataGenerator(
                             rotation_range=60,
                             featurewise_center=True,
                             featurewise_std_normalization=True,
                             width_shift_range=0.15,
                             height_shift_range=0.15,
                             zoom_range=0.2,
                             shear_range=10,
                             horizontal_flip=True,
                             vertical_flip=True)

datagen.fit(X_train)
X_valid = datagen.standardize(X_valid)

train_generator = datagen.flow(X_train, y_train, batch_size=batch_size)

model = LoadModel(img_shape, num_classes)


layer_dict = dict([(layer.name, layer) for layer in model.layers])
[layer.name for layer in model.layers]

# load json and create model
json_file = open('../experimentos/cnn_079_ndsb_nounk/model_079.json', 'r')
loaded_model_json = json_file.read()
json_file.close()
loaded_model = model_from_json(loaded_model_json)

# load weights into new model
loaded_model.load_weights("../experimentos/cnn_079_ndsb_nounk/best_model_079.hdf5")

layer_names = [layer.name for layer in model.layers]
for i in layer_dict.keys():
    index = layer_names.index(i)
    weights = loaded_model.layers[index].get_weights()
    model.layers[index].set_weights(weights)

model.add(Dense(num_classes, activation='softmax'))

for layer in model.layers[:25]:
    layer.trainable = False

model.summary()

opt = keras.optimizers.SGD(lr=0.0, momentum=0.9, nesterov=True)

model.compile(loss='categorical_crossentropy',
              optimizer=opt,
              metrics=['accuracy'])


model_path = "./model_fine_tuning_teste_6.hdf5" 

checkpoint = ModelCheckpoint(model_path,
        monitor='val_acc',
        verbose=1,
        save_best_only=True,
        mode='max')

lrate = LearningRateScheduler(step_decay)

model.fit_generator(train_generator,
                    steps_per_epoch=len(X_train) // batch_size,
                    validation_data=(X_valid, y_valid),
                    validation_steps=len(X_valid) // batch_size,
                    epochs=200,
                    callbacks=[lrate, checkpoint])

model_json = model.to_json()
with open("./model_fine_tuning_teste_6.json","w") as json_file:
    json_file.write(model_json)
print('Saved trained model at model_fine_tuning_teste_6.hdf5 and model_fine_tuning_teste_6.json')

predictions_valid = model.predict(X_valid, batch_size=batch_size)
predicted_labels_valid = np.argmax(predictions_valid, axis=1)
np.save("./complete_predictions_valid_ftteste6.npy", predictions_valid)
np.save("./predicted_labels_valid_ftteste6.npy", predicted_labels_valid)
np.save("./real_labels_valid_ftteste6.npy", y_valid)


predictions = model.predict(X_train, batch_size=batch_size)
predicted_labels = np.argmax(predictions, axis=1)
np.save("./complete_predictions_train_ftteste6.npy", predictions)
np.save("./predicted_labels_train_ftteste6.npy", predicted_labels)
np.save("./real_labels_train_ftteste6.npy", y_train)

print("Predictions saved")




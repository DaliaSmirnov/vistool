from beehive_infra.common.WebHelper import *
import pandas as pd
import ast
import os
import cv2
from dotenv import load_dotenv
load_dotenv(verbose=True)

# config
env = getenv_str('ENVIRONMENT', 'prod')
mode = getenv_str('MODE', 'local')
web = WebHelper(env, mode)


USER_NAME = 'daliasmirnov'
DATA_PATH = ''
org_img_path = '/Users/' + USER_NAME + '/Desktop/img/'
vistool_img_path = './img/'

# download images
def img_imp(id_list):
    for id in id_list:
        try:
            image_file = web.download_from_imaginary(id, org_img_path)
        except Exception:
            print(id)

def resize(org_img_path,vistool_img_path):
    for fn in os.listdir(org_img_path):
        try:
            img = cv2.imread(org_img_path + fn)

            scale_percent = 30  # percent of original size
            width = int(img.shape[1] * scale_percent / 100)
            height = int(img.shape[0] * scale_percent / 100)
            dim = (width, height)

            # resize image
            resized = cv2.resize(img, dim, interpolation=cv2.INTER_AREA)
            if fn.endswith('.jpeg'):
                cv2.imwrite(vistool_img_path + fn, resized)
            else:
                cv2.imwrite(vistool_img_path + fn.strip('.png') + '.jpeg', resized)
            print(fn, 'success')

        except AttributeError:
            print(fn, 'failed')


if __name__ == '__main__':
    # get imaginary ids
    df = pd.read_csv(DATA_PATH)
    id_list = list(df['target'].unique())

    # install images and resize them
    img_imp(id_list)
    resize(org_img_path,vistool_img_path)


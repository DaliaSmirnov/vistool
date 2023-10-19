from flask import Flask
from flask import request
from flask import send_from_directory
from flask import render_template
from werkzeug.utils import secure_filename

import VistoolNeighbors
import vgg_graph_2
import pandas as pd
import shutil

app = Flask(__name__, static_folder='static')

@app.route('/js/<path:path>')
def send_js(path):
  return send_from_directory('js', path)


@app.route("/thr_view/<path:path>")
def view(path):
  s = open('./img_txt.html').read()
  s = s.replace('PATH', path)
  s = s.replace('DATANAME', str(path).split('_thr_0')[0])
  return s


######################### Home Page #########################

UPLOAD_FOLDER = './data/'
ALLOWED_EXTENSIONS = {'txt', 'csv','parq','parquet'}
import os

@app.route("/home/<path:path>")
def home_view(path):
  s = open('./home.html').read()
  s = s.replace('PATH', path)
  return s


@app.route('/uploader', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':

        ngb_list = request.form.getlist('ngb')

        # user uploaded csv:
        imid_edges = pd.DataFrame()
        imid_file = request.files['imidfile']
        if imid_file and imid_file.filename.endswith('.csv'):
            data_type = imid_file.filename.split('.')[0]
            imid_file.save((str(UPLOAD_FOLDER + imid_file.filename)))
            id_list = pd.read_csv((str(UPLOAD_FOLDER+imid_file.filename)))
            id_list = list(id_list['im_id'].unique())
            imid_edges = VistoolNeighbors.prepare_edges(data_type, id_list, ngb_list)

        edges_df = pd.DataFrame()
        edges_file = request.files['edgesfile']
        if edges_file and (edges_file.filename.endswith('.parq') or edges_file.filename.endswith('.parquet')):
            data_type = edges_file.filename.split('.')[0]
            edges_file.save((str(UPLOAD_FOLDER + edges_file.filename)))
            edges_df = pd.read_parquet((str(UPLOAD_FOLDER + edges_file.filename)))
            if not list(edges_df.keys()) == ['source', 'target', 'weight', 'label']:
                return 'wrong edges file!'


        final_edges = pd.concat([edges_df,imid_edges])
        final_edges.to_parquet('/Users/daliasmirnov/PycharmProjects/ds-vistool/data/' + data_type + '.parq')
        vgg_graph_2.main(data_type, 0, '/Users/daliasmirnov/PycharmProjects/ds-vistool/data/' + data_type + '.parq')

        return 'file uploaded successfully, please enter in few moments: http://127.0.0.1:5001/thr_view/'+data_type+'_thr_0_p-1'

######################### Tree View #########################

@app.route("/tree_view/<path:path>")
def tree_view(path):
  s = open('tree.html').read()
  s = s.replace('PATH', path)
  return s


@app.route('/img/<path:path>')
def send_img(path):
  return send_from_directory('img', path)


@app.route('/apply/<path:path>', methods=['GET', 'POST'])
def apply(path):

    # get users filters:
    user_weights = {}
    labels = ['id','expense_type', 'amount', 'vendor', 'gemini', 'all']
    if request.method == 'POST':
        for lbl in labels:
            weight = request.form.get(lbl + '_text')
            if weight:
                user_weights[lbl] = weight
        user_labels = list(user_weights.keys())

        # apply filters on data and generate graph only if user gave them:
        if user_labels:
            edges_df = pd.read_parquet('/Users/daliasmirnov/PycharmProjects/ds-vistool/data/edges_files/wrong_amount_updated_edges.parq')
            data_type, tree_path = vgg_graph_2.generate_graph(edges_df, 'wrong_amount_updated_edges_user', user_weights)
            links_df = pd.read_parquet(tree_path)
            vgg_graph_2.create_semantic_graph(links_df, data_type)

        print(user_labels, user_weights)

        # install jsons
        if request.form.get('file_name'):
            file_name = request.form.get('file_name')
            print(file_name)
        if request.form.get('action1'):
            url = str(request.url).split('/')[-1]
            src = './js/' + url + '.json'
            dst = '/Users/daliasmirnov/Desktop/my_vis_jsons/' + file_name + '.json'
            shutil.copy(src, dst)
            print('success')


    s = open('./img_txt.html').read()
    s = s.replace('PATH', path.replace('apply','thr_view'))
    return s



if __name__ == '__main__':
    app.run(port=5001)


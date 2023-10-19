import pandas as pd
import numpy as np
from beehive_infra.common.DataHandler import *
from dotenv import load_dotenv
from beehive_infra.common.common_constants import FeatureName
load_dotenv(verbose=True)

os.environ['SERVICE_DATA_ROOT_FOLDER'] = "NexusData"
os.environ['SERVICE_DATA_BUCKET'] = "barmoach-ocr-production"
os.environ['MODE'] = "local"
os.environ['USE_DATADOG'] = "False"
os.environ['USE_REDIS_CACHE'] = "False"

dh = DataHandler('barmoach-ocr-production', 'NexusData')
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
import datetime
import re

def extract_num_from_string(string: str) -> int:
  return ''.join(re.findall('\d', string))


def get_data(im_id, ngb_list):
    i = 0
    result = pd.DataFrame(index=range(len(ngb_list)))
    try:
        melt = False
        solomon = dh.download_data(im_id, FeatureName.solomon, FileExtension.json)
        if 'fields' in solomon.keys():
            solomon=solomon.get('fields')

        elif 'extractedFields' in solomon.keys():
            solomon=solomon.get('extractedFields')
        elif 'amount' in solomon.keys():
            melt = True
        solomon = pd.DataFrame(solomon)
        if melt==True:
            solomon=solomon[:1]
            solomon = solomon.melt(var_name="name", value_name="value")


        date = dh.download_data(im_id, FeatureName.tx_date, FileExtension.json).get('conclusion')


    except:
        return None

    for ngb in ngb_list:
        weight=2
        if ngb == 'Amount':
            try:
                value = solomon.loc[solomon['name']=='amount','value'].astype(float).values
                # value = pd.cut(x=list(value), bins=[0, 10, 20, 50, 100, 1000000000],
                #        labels=['0-10', '10-20', '20-50', '50-100',
                #                'more then 100'])
                if value.to_list()==[]:
                    value = 'no amount'
            except:
                value='no amount'

        elif ngb in['Day_of_week','Year','Quarter','Month']:
            if not date:
                continue
            try:
                value = datetime.datetime.strptime(date, '%d/%m/%Y')
                if ngb == 'Year' :
                    value = value.year
                    weight = 2
                elif ngb == 'Day_of_week':
                    value=value.weekday()

                elif ngb == 'Quarter':
                    value=(value.month-1)//3+1
                    weight = 2

                elif ngb == 'Month':
                    value = value.month

            except:
                value = 'no date'

        else:
            try:
                value =  str(solomon.loc[solomon['name']==ngb,'value'].values)
                if ngb == 'country':
                    weight = 100
            except:
                value = 'no country'
            try:
                if ngb == 'expenseType':
                    weight = 80
                    value=extract_num_from_string(value)
            except:
                value = 'no expenseType'

        result.loc[i,'source'] = value
        result.loc[i,'label'] = ngb
        result.loc[i,'weight'] = weight
        i +=1

    result['target'] = im_id
    result = result[['source','target','weight','label']]

    return result


def prepare_edges(data_type, id_list, ngb_list):
    start_time = time.time()
    batch_size = 1000
    batches = 1
    final_df = pd.DataFrame()

    for i in range(batches):
        print('batch '+str(i))
        edges_df = []
        try:
            with ThreadPoolExecutor(max_workers=50) as executor:
                execute_futures = {executor.submit(get_data, im,ngb_list) for im in id_list[i*(batch_size):(i+1)*(batch_size)]}
                for future in concurrent.futures.as_completed(execute_futures,timeout=500):
                    try:
                        if (future.result() is not None):
                            edges_df.append(future.result())
                    except Exception as exc:
                        print('Exception on {}\n'.format(future[future]) + str(exc))
        except:
            pass

        final = pd.concat(edges_df)
        final = pd.DataFrame(final)
        final['source'] = final['source'].astype(str)

        # map expense type
        final['source'] = np.where(final['label'] == 'expenseType', final['source'].replace({'25': 'Restaurant', '[102]':'Monthly_bills', '[20]':'Professional Services',
                                                  '34':'Tolls', '27':'Office Electronic & Tools', '22':'Public Transportation', '[5]':'hotel',5:'hotel',
                                                  '31':'parking', '4':'Car Rental', '101':'flights', '21':'Entertainment',
                                                  '6':'Conferences', '103':'Travel Agency', '30':'Communication','18':'Fuel Expenses',
                                                  '33':'flights','0.0':'NoExpenseType'}), final['source'])

        final_df=final_df.append(final)
        elapsed = time.time() - start_time
        print("elapsed:", elapsed)


    final_df.to_parquet('/Users/daliasmirnov/PycharmProjects/ds-vistool/data/' + data_type + '.parq')
    return final_df


# id_list = ['620ba98f3400006c006ec1d1', '615fcd0c3300007b2d80c8d3', '61e6946732000084001960ea']
# df = pd.read_parquet('/Users/daliasmirnov/Downloads/paraphrase_xlm_multilingual_hotels_and_restaurants_20k.parquet')
# id_list = list(df['im_id'].unique())[:1000]
# ngb_list = ['country', 'expenseType']
enrichment_asset = dh.download_data('621494ff320000540024ce31', FeatureName.enrichment_asset, FileExtension.json)
# rec_list = enrichment_asset['recommendations']['extractedFields'].keys()
# extractors_list = list(pd.DataFrame(enrichment_asset['extractorsRawData'])['extractor'].values)
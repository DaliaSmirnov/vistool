# vistool

1. clone to the repo
2. make sure you have you create two new directories: "js" and "data"
3. make sure to replace all of my private paths to your local path (just ctrl+f for daliasmirnov and change it)
4. make sure that you've got all of the neccesary packages

5. run app.py
6. open this url: http://127.0.0.1:5001/home/a
7. upload your parquet file in "Custom Edges File:Choose file"
   your parquet file should have 4 columns: source,target,weight,label. label describes the source node.
   please take a look at the "dummy_data.parq" file in the repo (try to run a demo with this file)
8. upload the file and you'll get redircted to other path, please open it.
  ("file uploaded successfully, please enter in few moments: http://127.0.0.1:5001/thr_view/dummy_data_thr_0_p-1")
9. that's it! now you can see the graph, to enter sub graph just click on a node and get deeper.

10. to view the RAW dataframe of each node and it's cluster, put a breaking point in row num 159 in vgg_graph_2.py and "links_df" is your dataframe with all of the data :)

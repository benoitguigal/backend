#!/usr/bin/env python2
# -*- coding: utf-8 -*-

### import basics
import sys, os, io, fnmatch, re, datetime, hashlib, unicodedata, shutil

import traceback
import json
import itertools
import time
import operator
import simplejson
from collections import Iterable
from collections import OrderedDict
from pandas.io.json import json_normalize
from collections import deque


#### interact with datasets
import gzip
#from pandasql import sqldf
import elasticsearch
from elasticsearch import Elasticsearch, helpers
import pandas as pd

#### parallelize
# import concurrent.futures
#import threading
from multiprocessing import Process
import uuid

# recipes

### api
from flask import Flask,jsonify,Response, abort,request
from flask_restplus import Resource,Api,reqparse
from werkzeug.utils import secure_filename
from werkzeug.serving import run_simple
from werkzeug.wsgi import DispatcherMiddleware

# matchID imports
import parsers
import config
from tools import replace_dict
from recipes import *
from log import Log, err

def allowed_upload_file(filename=None):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.conf["global"]["data_extensions"]


def allowed_conf_file(filename=None):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.conf["global"]["recipe_extensions"]


config.init()
config.read_conf()

app = Flask(__name__)
api=Api(app,version="0.1",title="matchID API",description="API for data matching developpement")
app.config['APPLICATION_ROOT']=config.conf["global"]["api"]["prefix"]

@api.route('/conf/', endpoint='conf' )
class Conf(Resource):
	def get(self):
		'''get all configured elements
		Lists all configured elements of the backend, as described in the yaml files :
		- global configuration
		- projects :
		  - datasets
		  - recipes'''
		try:
			config.read_conf()
			return config.conf["global"]
		except:
			return {"error": "problem while reading conf"}

@api.route('/upload/', endpoint='upload')
class Upload(Resource):
	def get(self):
		'''list uploaded resources'''
		return list([filenames for root, dirnames, filenames in os.walk(config.conf["global"]["paths"]["upload"])])[0]

	@api.expect(parsers.upload_parser)
	def post(self):
		'''upload multiple tabular data files, .gz or .txt or .csv'''
		response={"upload_status":{}}
		args = parsers.upload_parser.parse_args()
		for file in args['file']:
			if (allowed_upload_file(file.filename)):
				try:
					file.save(os.path.join(config.conf["global"]["paths"]["upload"], secure_filename(file.filename)))
					response["upload_status"][file.filename]="ok"
				except:
					response["upload_status"][file.filename]=err()
			else:
				response["upload_status"][file.filename]="extension not allowed"
		return response

@api.route('/upload/<file>', endpoint='upload/<file>')
@api.doc(parmas={'file': 'file name of a previously uploaded file'})
class actionFile(Resource):
	def get(self,file):
		'''get back uploaded file'''
		filetype="unknown"
		pfile=os.path.join(config.conf["global"]["paths"]["upload"],file)
		try:
			df=pd.read_csv(pfile,nrows=100)
			filetype="csv"
		except:
			pass
		return {"file": file, "type_guessed": filetype}

	def delete(self,file):
		'''deleted uploaded file'''
		try:
			pfile=os.path.join(config.conf["global"]["paths"]["upload"],file)
			os.remove(pfile)
			return {"file": file, "status": "deleted"}
		except:
			api.abort(404,{"file": file, "status": err()})


@api.route('/conf/<project>/', endpoint='conf/<project>')
@api.doc(parms={'project': 'name of a project'})
class DirectoryConf(Resource):
	def get(self,project):
		'''get configuration files of a project'''
		config.read_conf()
		if project in list(config.conf["global"]["projects"].keys()):
			return config.conf["global"]["projects"][project]
		else:
			api.abort(404)

	@api.expect(parsers.conf_parser)
	def post(self,project):
		'''(KO) import a zipped project'''
		if (directory != "conf"):
			response={"upload_status":{}}
			args = parsers.conf_parser.parse_args()
			for file in args['file']:
				if (allowed_conf_file(file.filename)):
					try:
						file.save(os.path.join(config.conf["global"]["paths"]["conf"][project], secure_filename(file.filename)))
						response["upload_status"][file.filename]="ok"
					except:
						response["upload_status"][file.filename]=err()
				else:
					response["upload_status"][file.filename]="extension not allowed"
				config.read_conf()
				response["yaml_validator"]=config.conf["global"]["projects"][project]
			return response
		else:
			api.abort(403)

	def put(self,project):
		'''create a project'''
		if (project == "conf"):
			api.abort(403)
		elif project in config.conf["global"]["projects"].keys():
			api.abort(400, 'project "{}" already exists'.format(project))
		else:
			try:
				dirname=os.path.join(config.conf["global"]["paths"]["projects"],project)
				os.mkdir(dirname)
				os.mkdir(os.path.join(dirname,'recipes'))
				os.mkdir(os.path.join(dirname,'datasets'))
				config.read_conf()
				return {"message": "{} successfully created".format(project)}
			except:
				api.abort(400,err())

	def delete(self,project):
		'''delete a project'''
		if (project == "conf"):
			api.abort(403)
		elif project in config.conf["global"]["projects"].keys():
			response={project: "not deleted"}
			try:
				dirname=os.path.join(config.conf["global"]["paths"]["projects"],project)
				shutil.rmtree(dirname)
				response[project]="deleted"
			except:
				response[project]="deletion failed - "+err()
			config.read_conf()
			#response["yaml_validator"]=config.conf["global"]["projects"][project]
			return response
		else:
			api.abort(404)

@api.route('/conf/<project>/<path:file>', endpoint='conf/<project>/<path:file>')
class FileConf(Resource):
	def get(self,project,file):
		'''get a text/yaml configuration file from project'''
		try:
			config.read_conf()
			if (file in config.conf["global"]["projects"][project]["files"]):
				try:
					pfile=os.path.join(config.conf["global"]["projects"][project]["path"],file)
					with open(pfile) as f:
						return Response(f.read(),mimetype="text/plain")
				except:
					api.abort(404)
			else:
				api.abort(404)
		except:
			api.abort(404)

	def delete(self,project,file):
		'''delete a text/yaml configuration file from project'''
		if (project != "conf"):
			if (file in config.conf["global"]["projects"][project]["files"]):
				try:
					pfile=os.path.join(config.conf["global"]["projects"][project]["path"],file)
					os.remove(pfile)
					config.read_conf()
					return jsonify({"conf": project, "file":file, "status": "removed"})
				except:
					api.abort(403)

	@api.expect(parsers.yaml_parser)
	def post(self,project,file):
		'''upload a text/yaml configuration file to a project'''
		if (project != "project"):
			args = parsers.yaml_parser.parse_args()
			filecontent=args['yaml']
			if (allowed_conf_file(file)):
				try:
					test = config.ordered_load(filecontent)
				except:
					api.abort(400,{file: {"saved" : "ko - "+err()}})

				try:
					pfile=os.path.join(config.conf["global"]["projects"][project]["path"],file)
					with open(pfile,'w') as f:
						f.write(filecontent.encode("utf-8", 'ignore'))
					response={file: {"saved": "ok"}}
					config.read_conf()
					response[file]["yaml_validator"]=config.conf["global"]["projects"][project]["files"][file]
					return response
				except:
					api.abort(400,{file: {"saved" : "ko - "+err()}})
			else:
				api.abort(403)
		else:
			api.abort(403)



@api.route('/datasets/', endpoint='datasets')
class ListDatasets(Resource):
	def get(self):
		'''get json of all configured datasets'''
		config.read_conf()
		return config.conf["datasets"]

@api.route('/datasets/<dataset>/', endpoint='datasets/<dataset>')
class DatasetApi(Resource):
	def get(self,dataset):
		'''get json of a configured dataset'''
		config.read_conf()
		if (dataset in config.conf["datasets"].keys()):
			try:
				response = dict(config.conf["datasets"][dataset])
				try:
					ds=Dataset(dataset)
					response["type"] = ds.connector.type
				except:
					pass
				return response
			except:
				api.abort(500)
		else:
			api.abort(404)

	def post(self,dataset):
		'''get sample of a configured dataset, number of rows being configured in connector.samples'''
		ds=Dataset(dataset)
		if (ds.connector.type == "elasticsearch"):
	 		ds.select={"query":{"function_score": {"query":ds.select["query"],"random_score":{}}}}
		ds.init_reader()
		try:
			df=next(ds.reader,"")
			schema=df.dtypes.apply(lambda x: str(x)).to_dict()
			if (type(df) == str):
				try :
					return {"data":[{"error": "error: no such file {}".format(ds.file)}]}
				except:
					return {"data":[{"error": "error: no such table {}".format(ds.table)}]}
			df=df.head(n=ds.connector.sample).reset_index(drop=True)
			return {"data": list(df.fillna("").T.to_dict().values()), "schema": schema}
		except:
			error=err()
			try:
				return {"data":[{"error": "error: {} {}".format(error,ds.file)}]}
			except:
				return {"data":[{"error": "error: {} {}".format(error,ds.table)}]}


	def delete(self,dataset):
		'''delete the content of a dataset (currently only working on elasticsearch datasets)'''
		ds=Dataset(dataset)
		if (ds.connector.type == "elasticsearch"):
			try:
				ds.connector.es.indices.delete(index=ds.table, ignore=[400, 404])
				config.log.write("detete {}:{}/{}".format(ds.connector.host,ds.connector.port,ds.table))
				ds.connector.es.indices.create(index=ds.table)
				config.log.write("create {}:{}/{}".format(ds.connector.host,ds.connector.port,ds.table))
				return {"status": "ok"}
			except:
				return {"status": "ko - " + err()}
		else:
			return api.abort(403)


@api.route('/datasets/<dataset>/<action>', endpoint='datasets/<dataset>/<action>')
class pushToValidation(Resource):
	def get(self,dataset,action):
		'''(KO) does nothing yet'''
		if (action=="yaml"):
			return
	def put(self,dataset,action):
		'''action = validation : configure the frontend to point to this dataset'''
		import config
		config.init()
		config.read_conf()
		if (action=="validation"):
			if (not(dataset in config.conf["datasets"].keys())):
				return api.abort(404,{"dataset": dataset, "status": "dataset not found"})
			if not("validation" in config.conf["datasets"][dataset].keys()):
				return api.abort(403,{"dataset": dataset, "status": "validation not allowed"})
			if ((config.conf["datasets"][dataset]["validation"]==True)|(isinstance(config.conf["datasets"][dataset]["validation"], OrderedDict))):
				try:
					props = {}
					try:
						cfg=deepupdate(config.conf["global"]["validation"],config.conf["datasets"][dataset]["validation"])
					except:
						cfg=config.conf["global"]["validation"]
					for conf in cfg.keys():
						configfile=os.path.join(config.conf["global"]["paths"]["validation"],secure_filename(conf+".json"))
						dic={
							"prefix": config.conf["global"]["api"]["prefix"],
							"domain": config.conf["global"]["api"]["domain"],
							"dataset": dataset
						}
						props[conf] = replace_dict(cfg[conf],dic)
						# with open(configfile, 'w') as outfile:
						# 	json.dump(props[config],outfile,indent=2)
					return {"dataset": dataset, "status": "to validation", "props": props}
				except :
						return api.abort(500,{"dataset": dataset, "status": "error: "+err()})
			else:
				return api.abort(403,{"dataset": dataset, "status": "validation not allowed"})
		elif (action=="search"):
			if (not(dataset in config.conf["datasets"].keys())):
				return api.abort(404,{"dataset": dataset, "status": "dataset not found"})
			if not("search" in config.conf["datasets"][dataset].keys()):
				return api.abort(403,{"dataset": dataset, "status": "search not allowed"})
			if ((config.conf["datasets"][dataset]["search"]==True)|(isinstance(config.conf["datasets"][dataset]["search"], OrderedDict))):
				try:
					props = {}
					try:
						cfg=deepupdate(config.conf["global"]["search"],config.conf["datasets"][dataset]["search"])
					except:
						cfg=config.conf["global"]["search"]
					for config in cfg.keys():
						configfile=os.path.join(config.conf["global"]["paths"]["search"],secure_filename(config+".json"))
						dic={
							"prefix": config.conf["global"]["api"]["prefix"],
							"domain": config.conf["global"]["api"]["domain"],
							"dataset": dataset
						}
						props[config] = replace_dict(cfg[config],dic)
						# with open(configfile, 'w') as outfile:
						# 	json.dump(props[config],outfile,indent=2)
					return {"dataset": dataset, "status": "to search", "props": props}
				except :
						return api.abort(500,{"dataset": dataset, "status": "error: "+err()})
			else:
				return api.abort(403,{"dataset": dataset, "status": "search not allowed"})

		else:
			api.abort(404)

	def post(self,dataset,action):
		'''(KO) search into the dataset'''
		if (action=="_search"):
			return {"status": "in dev"}
		else:
			api.abort(403)




@api.route('/recipes/', endpoint='recipes')
class ListRecipes(Resource):
	def get(self):
		'''get json of all configured recipes'''
		return config.conf["recipes"]

@api.route('/recipes/<recipe>/', endpoint='recipes/<recipe>')
class RecipeApi(Resource):
	def get(self,recipe):
		'''get json of a configured recipe'''
		try:
			return config.conf["recipes"][recipe]
		except:
			api.abort(404)


@api.route('/recipes/<recipe>/<action>', endpoint='recipes/<recipe>/<action>')
class RecipeRun(Resource):
	def get(self,recipe,action):
		'''retrieve information on a recipe
		** action ** possible values are :
		- ** status ** : get status (running or not) of a recipe
		- ** log ** : get log of a running recipe'''
		if (action=="status"):
			#get status of job
			try:
				return {"recipe":recipe, "status": config.jobs_list[str(recipe)]}
			except:
				return {"recipe":recipe, "status": "down"}
		elif (action=="log"):
			#get logs
			try:
				# try if there is a current log
				with open(config.jobs[recipe].log.file, 'r') as f:
					response = f.read()
					return Response(response,mimetype="text/plain")
			except:
				try:
					# search for a previous log
					a = config.conf["recipes"][recipe] # check if recipe is declared
					logfiles = [os.path.join(config.conf["global"]["log"]["dir"],f)
								for f in os.listdir(config.conf["global"]["log"]["dir"])
								if re.match(r'^.*-' + recipe + '.log$',f)]
					logfiles.sort()
					file = logfiles[-1]
					with open(file, 'r') as f:
						response = f.read()
						return Response(response,mimetype="text/plain")
				except:
					api.abort(404)
		api.abort(403)

	@api.expect(parsers.live_parser)
	def post(self,recipe,action):
		'''apply recipe on posted data
		** action ** possible values are :
		- ** apply ** : apply recipe on posted data
		'''
		if (action=="apply"):
			args = parsers.live_parser.parse_args()
			file=args['file']
			if not (allowed_upload_file(file.filename)):
				api.abort(403)
			r=Recipe(recipe)
			r.input.chunked=False
			r.input.file=file.stream
			r.init(test=True)
			r.run()
			if isinstance(r.df, pd.DataFrame):
				df=r.df.fillna("")
				try:
					return jsonify({"data": df.T.to_dict().values(), "log": str(r.log.writer.getvalue())})
				except:
					df=df.applymap(lambda x: str(x))
					return jsonify({"data": df.T.to_dict().values(), "log": str(r.log.writer.getvalue())})
			else:
				return {"log": r.log.writer.getvalue()}


	def put(self,recipe,action):
		'''test, run or stop recipe
		** action ** possible values are :
		- ** test ** : test recipe on sample data
		- ** run ** : run the recipe
		- ** stop ** : stop a running recipe (soft kill : it may take some time to really stop)
		'''
		config.read_conf()
		if (action=="test"):
			try: 
				callback = config.manager.dict()
				r=Recipe(recipe)
				r.init(test=True, callback=callback)
				r.set_job(Process(target=thread_job,args=[r]))
				r.start_job()
				r.join_job()
				r.df = r.callback["df"]
				r.log = r.callback["log"]
				r.errors = r.callback["errors"]

			except:
				return {"data": [{"result": "failed"}], "log": "Ooops: {}".format(err())}
			if isinstance(r.df, pd.DataFrame):
				df=r.df.fillna("")
				if (r.df.shape[0]==0):
					return {"data": [{"result": "empty"}], "log": r.callback["log"]}
				try:
					return jsonify({"data": df.T.to_dict().values(), "log": r.callback["log"]})
				except:
					df=df.applymap(lambda x: unicode(x))
					return jsonify({"data": df.T.to_dict().values(), "log": r.callback["log"]})
			else:
				return {"data": [{"result": "empty"}], "log": r.callback["log"]}
		elif (action=="run"):
			#run recipe (gives a job)
			try:
				if (recipe in list(config.jobs.keys())):
					status=config.jobs[recipe].job_status()
					if (status=="up"):
						return {"recipe": recipe, "status": status}
			except:
				api.abort(403)

			config.jobs[recipe]=Recipe(recipe)
			config.jobs[recipe].init()
			config.jobs[recipe].set_job(Process(target=thread_job,args=[config.jobs[recipe]]))
			config.jobs[recipe].start_job()
			return {"recipe":recipe, "status": "new job"}
		elif (action=="stop"):
			try:
				if (recipe in list(config.jobs.keys())):
					thread=Process(config.jobs[recipe].stop_job())
					thread.start()
					return {"recipe": recipe, "status": "stopping"}
			except:
				api.abort(404)


@api.route('/jobs/', endpoint='jobs')
class jobsList(Resource):
	def get(self):
		'''retrieve jobs list
		'''
		# response = jobs.keys()
		response = {"running": [], "done": []}
		for recipe in config.jobs_list.keys():
			# logfile = config.jobs[recipe].job.log.file
			logfile = config.jobs_list[recipe]["log"]
			# status = job.job_status()
			status = config.jobs_list[recipe]["status"]
			try: 
				if (status != "down"):
					response["running"].append({ "recipe": recipe,
												 "file": re.sub(r".*/","", logfile),
												 "date": re.sub(r".*/(\d{4}.?\d{2}.?\d{2})T(..:..).*log",r"\1-\2",logfile)
												  })
			except:
				response["running"]=[{"error": "while trying to get running jobs list"}]
		logfiles = [f
							for f in os.listdir(config.conf["global"]["log"]["dir"])
							if re.match(r'^.*.log$',f)]
		for file in logfiles:
			recipe = re.search(".*-(.*?).log", file, re.IGNORECASE).group(1)
			date = re.sub(r"(\d{4}.?\d{2}.?\d{2})T(..:..).*log",r"\1-\2", file)
			if (recipe in config.conf["recipes"].keys()):
				try:
					if (response["running"][recipe]["date"] != date):
						try:
							response["done"].append({"recipe": recipe, "date": date, "file": file})
						except:
							response["done"]=[{"recipe": recipe, "date": date, "file": file}]
				except:
					try:
						response["done"].append({"recipe": recipe, "date": date, "file": file})
					except:
						response["done"]=[{"recipe": recipe, "date": date, "file": file}]

		return response

if __name__ == '__main__':
	config.read_conf()
	app.config['DEBUG'] = config.conf["global"]["api"]["debug"]

	config.log=Log("main")

	# recipe="dataprep_snpc"
	# r=Recipe(recipe)
	# r.init()
	# r.run()

    # Load a dummy app at the root URL to give 404 errors.
    # Serve app at APPLICATION_ROOT for localhost development.
	application = DispatcherMiddleware(Flask('dummy_app'), {
		app.config['APPLICATION_ROOT']: app,
	})
	run_simple(config.conf["global"]["api"]["host"], config.conf["global"]["api"]["port"], application, processes=config.conf["global"]["api"]["processes"], use_reloader=config.conf["global"]["api"]["use_reloader"])

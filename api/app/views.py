from flask import request
from flask import json
from app import app
from elasticsearch import Elasticsearch
import os
from random import randint

host = 'http://{}:{}@ip-10-0-0-10:9200/'.format(os.environ['ELASTIC_USER'], os.environ['ELASTIC_PASS'])
es = Elasticsearch([host], timeout=90)

@app.route('/topics', methods=['POST'])
def get_recommendations():
    data = request.get_json()
    topics = data['topics']
    simple = data.get('simple', True)
    if simple:
        return json.dumps(query_simple(topics))
    else:
        return json.dumps(query_custom(topics))

@app.route('/random')
def get_random():
    seed = randint(-10**6, 10**6)
    query = {
       "size": 1,
       "query": {
          "function_score": {
             "functions": [
                {
                   "random_score": {
                      "seed": seed
                   }
                }
             ]
          }
       }
    }
    return json.dumps(_exec_query(query)[0])


def query_custom(topics):
    should_clause = [
        {'constant_score': {
            'filter' : {
                'match': { 'topics' :  topic} }}}
        for topic in topics
    ]
    query = {
        'size': 10,
        'query': {
            'function_score': {
                'query': {
                    'bool': {'should': should_clause }
                },
                'script_score' : {
                    'script' : {
                        'inline': '- Math.abs(_score/doc[\'num_topics\'].value - 0.75)'
                    }
                }
            }
        }
    }
    return {'recommendations': _exec_query(query)}

def query_simple(topics):
    should_clause = [
        {'match': { 'topics' :  topic} }
        for topic in topics
    ]
    query = {
        'size': 10,
        'query': {
            'bool': {'should': should_clause}
        }
    }
    return {'recommendations': _exec_query(query)}

def _exec_query(query):
    results = es.search(index='documents', body=query)
    app.logger.info('a simple request took {} milliseconds'.format(results['took']))
    parsed_results = []
    for result in results['hits']['hits']:
        parsed_result = result['_source']
        parsed_result['score'] = result['_score']
        parsed_results.append(parsed_result)
    return parsed_results

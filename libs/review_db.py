import json
import logging
import os
import pandas as pd

from .TfidfModel import TFIDFModel
logging.basicConfig(format='%(filename)s:%(lineno)d %(message)s')
log = logging.getLogger(__name__)
log.setLevel('INFO')

CONFIG = json.load(open("./../config.json"))
data_folder = os.path.join(os.environ['DATA_DIR'], CONFIG['dataset'])

class ReviewDB():
    def __init__(self, data_folder=data_folder):
        self.entity_db_dict = {
            "all": EntityDB("all", data_folder)
        }
        self.tfidf_dict = {
            name: TFIDFModel(db) for name, db in self.entity_db_dict.items()
        }
        self.tfidf_bigram_dict = {
            name: TFIDFModel(db, 2) for name, db in self.entity_db_dict.items()
        }

    def _add_ent(self, entity_id):
        db = EntityDB("all", data_folder)
        self.entity_db_dict[entity_id] = db
        self.tfidf_dict[entity_id] = TFIDFModel(db)
        self.tfidf_bigram_dict[entity_id] = TFIDFModel(db, 2)

    def _db(self, entity_id):
        if not entity_id in self.entity_db_dict:
            self._add_ent(entity_id)
        return self.entity_db_dict[entity_id]

    def get_reviews(self, entity_id, reviews_id):
        db = self._db(entity_id)
        return db.get_review_from_id(reviews_id)

    def get_cluster(self, entity_id, cluster_id):
        db = self._db(entity_id)
        return db.get_cluster_from_id(cluster_id)

    def get_centroids(self, entity_id, cluster_id):
        db = self._db(entity_id)
        return db.get_centroids_from_id(cluster_id)

    def get_topwords(self, entity_id, cluster_id, k=1):
        if not entity_id in self.entity_db_dict:
            self._add_ent(entity_id)
        if k == 1:
            return self.tfidf_dict[entity_id].top_k(cluster_id)
        elif k == 2:
            return self.tfidf_bigram_dict[entity_id].top_k(cluster_id)
        else:
            return Exception("Invalid value {} for k. There is only support for k=1 and k=2".format(k))

class EntityDB():
    def __init__(self, entity_id, data_folder):
        if entity_id != "all":
            data_folder = os.path.join(os.path.join(data_folder, 'hotel-clusters'), entity_id)
        try:
            cluster_file=os.path.join(data_folder, 'clusters.csv')
            clusters_df = pd.read_csv(cluster_file, index_col=0)
        except FileNotFoundError:
            cluster_file=os.path.join(data_folder, 'attr.csv')
            clusters_df = pd.read_csv(cluster_file, index_col=0)
        centroids_file=os.path.join(data_folder, 'centroids.csv')
        log.info(cluster_file + ' loaded')
        if centroids_file is not None:
            centroids_df = pd.read_csv(centroids_file)
            log.info(centroids_file + ' loaded')
        else:
            centroids_df = None

        self.centroids_df = centroids_df
        self.clusters_df = clusters_df

    def get_review_from_id(self, _id):
        '''
        Args:
                _id: id for a review or a cluster

            Returns:
                list of review objects
            Note: this is the main entrypoint for retrieving reviews with a given id
        '''
        id_list = self.decode_id(_id)
        return self.fetch_reviews(id_list)


    def get_cluster_from_id(self, _id):
        '''
        Args:
                _id: id for a cluster
            Returns:
                a dataframe row for the cluster centroid
        '''
        return self.centroids_df.query(f'cid == "{_id}"')

    def get_centroids_from_id(self, _id):
        if _id is not None:
            clayer = len(_id.split('-'))
            layer_centroids_df = self.centroids_df[self.centroids_df['clayer'] == clayer]  
            cur_centroids_df = layer_centroids_df[layer_centroids_df['cid'].str.startswith(_id + '-')]
            if cur_centroids_df.shape[0] == 0:
                return self.get_reviews(_id)
            return cur_centroids_df
        return self.centroids_df[self.centroids_df['clayer'] == 0]

    def decode_id(self, _id):
        '''
        Args:
                _id: id for a review or a cluster

            Returns:
                list of strings: [review_id1, review_id2] for all reviews in the review or cluster _id
            Note: helper function
        '''
        if _id == "all": #special case for querying over all reviews in the db
            return list(self.clusters_df['review_id'])
        if _id is None or _id == []:
            return None
        if type(_id) is int: #if review
            return [_id]
        else: #if cluster
            cluster_history = _id.split('-')
            condition = list(map(lambda i: f'L{i} == {cluster_history[i]}', range(len(cluster_history))))
            relevant_subset = self.clusters_df.query(' and '.join(condition))
            return list(relevant_subset['review_id'])

    def fetch_reviews(self, id_list):
        '''
        Args:
                id_list: list of review id strings

            Returns:
                list of review objects
            Note: helper function
        '''
        if not id_list:
            return None
        matches = self.clusters_df.review_id.isin(id_list)
        review_match_df = self.clusters_df[matches]
        return review_match_df

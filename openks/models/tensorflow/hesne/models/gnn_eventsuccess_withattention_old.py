import sys
import sklearn.metrics as metrics
import copy
# import pickle
import time

from layers.layers import *
from layers.aggregators import *
from models.basic_model import BasicModel
from utils.data_manager import *

class GnnEventModel_withattention_old(BasicModel):
    def __init__(self, args):
        super().__init__(args)

    def default_params(cls):
        params = dict(super().default_params())
        return params

    def get_log_file(self):
        log_file = 'h_' + str(self.params['hidden_size']) + '_b_' + str(self.params['batch_event_numbers']) \
                    + '_l_' + str(self.params['learning_rate']) + '_d_' + str(self.params['decay']) + '_ds_' \
                    + str(self.params['decay_step']) + '_k_' + str(self.params['keep_prob']) + '_'+str(self.params['his_type'])+'_'\
                    + str(self.params['max_his_num']) + '_n_' + str(self.params['negative_ratio']) + '_ns_' + str(self.params['negative_sampling']) + '_old.log'
        return log_file

    def get_checkpoint_dir(self):
        checkpoint_dir = 'h_' + str(self.params['hidden_size']) + '_b_' + str(self.params['batch_event_numbers']) \
                    + '_l_' + str(self.params['learning_rate']) + '_d_' + str(self.params['decay']) + '_ds_' \
                    + str(self.params['decay_step']) + '_k_' + str(self.params['keep_prob']) + '_'+str(self.params['his_type'])+'_'\
                    + str(self.params['max_his_num']) + '_n_' + str(self.params['negative_ratio']) + '_ns_' + str(self.params['negative_sampling']) + 'old'
        return checkpoint_dir

    def make_model(self):
        with tf.variable_scope('graph_model'):
            self.prepare_specific_graph_model()
            self.ops['loss'], self.ops['node_vec'], self.ops['node_cel'], self.ops['pred'], \
                                                    self.ops['neg_pred'] = self.build_specific_graph_model()
            self.ops['loss_eval'], self.ops['node_vec_eval'], self.ops['node_cel_eval'], \
                            self.ops['predict'], self.ops['neg_predict'] = self.build_specific_eval_graph_model()
            self.ops['global_step'] = tf.Variable(0, name='global_step', trainable=False)
        print('model build')

    def _create_placeholders(self):
            self.placeholders['events_nodes_ph'] = [tf.placeholder(tf.int32, shape=[None],
                                                    name='event%i_ph'%event)
                                                    for event in range(self._eventnum_batch)]

            self.placeholders['events_nodes_type_ph'] = [tf.placeholder(tf.int32, shape=[None],
                                                        name='event%i_type_ph'%event)
                                                        for event in range(self._eventnum_batch)]

            self.placeholders['events_nodes_history_ph'] = [tf.placeholder(tf.int32, shape=[None, self._max_his_num, self._type_num],
                                                        name='event%i_histrory_ph'%event)
                                                        for event in range(self._eventnum_batch)]
            #
            # self.placeholders['events_nodes_history_deltatime_ph'] = [tf.placeholder(tf.float64, shape=[None, self._max_his_num],
            #                                             name='event%i_histrory_deltatime_ph'%event)
            #                                             for event in range(self._eventnum_batch)]

            self.placeholders['events_partition_idx_ph'] = [tf.placeholder(tf.int32, shape=[self._num_node],
                                                        name='event%i_partition_idx_ph'%event)
                                                        for event in range(self._eventnum_batch)]

            # self.placeholders['events_sub_ph'] = [tf.placeholder(tf.int32, shape=[None, self._type_num], name='event%i_sub_ph'%event)
            #                                       for event in range(self._eventnum_batch)]

            self.placeholders['nodes_embedding_ph'] = tf.placeholder(tf.float64,
                                                    shape=[self._num_node, self._h_dim], name='node_embedding_ph')

            self.placeholders['nodes_cellstates_ph'] = tf.placeholder(tf.float64,
                                                    shape=[self._num_node, self._h_dim], name='node_cellstates_ph')

            self.placeholders['negevents_nodes_ph'] = [[tf.placeholder(tf.int32, shape=[None],
                                                    name='event%i_neg%i_ph'%(event, neg))
                                                    for neg in range(self._neg_num)]
                                                    for event in range(self._eventnum_batch)]

            self.placeholders['negevents_nodes_type_ph'] = [[tf.placeholder(tf.int32, shape=[None],
                                                    name='event%i_neg%i_type_ph'%(event, neg))
                                                    for neg in range(self._neg_num)]
                                                    for event in range(self._eventnum_batch)]

            self.placeholders['negevents_nodes_history_ph'] = [[tf.placeholder(tf.int32,
                                                        shape=[None, self._max_his_num, self._type_num],
                                                        name='event%i_neg%i_histrory_ph'%(event, neg))
                                                        for neg in range(self._neg_num)]
                                                        for event in range(self._eventnum_batch)]

            # self.placeholders['nodes_history_ph'] = tf.placeholder(tf.int32,
            #                             shape=[self._num_node, self._max_his_num, self._type_num], name='histrory_ph')

            # self.placeholders['nodes_history_deltatime_ph'] = tf.placeholder(tf.int32,
            #                             shape=[self._num_node, self._max_his_num], name='histrory_ph')

            # self.placeholders['negevents_nodes_history_deltatime_ph'] = [[tf.placeholder(tf.float64,
            #                                             shape=[None, self._max_his_num],
            #                                             name='event%i_neg%i_histrory_deltatime_ph'%(event, neg))
            #                                             for neg in range(self._neg_num)]
            #                                             for event in range(self._eventnum_batch)]

            self.placeholders['is_train'] = tf.placeholder(tf.bool, name='is_train')

            self.placeholders['is_init'] = tf.placeholder(tf.bool, name='is_init')

            self.placeholders['keep_prob'] = tf.placeholder(tf.float64, name='keep_prob')
            # self.placeholders['is_init'] = tf.placeholder(tf.bool, shape=[self._num_node], name='is_init')

            self.placeholders['has_neighbor'] = [tf.placeholder(tf.bool, shape=[None],
                                            name='event%i_hasneighbor_ph'%event)
                                            for event in range(self._eventnum_batch)]

            self.placeholders['has_neighbor_neg'] = [[tf.placeholder(tf.bool, shape=[None],
                                            name='event%i_neg%i_hasneighbor_ph'%(event, neg))
                                            for neg in range(self._neg_num)]
                                            for event in range(self._eventnum_batch)]

            # self.placeholders['events_deltatime_ph'] = [tf.placeholder(tf.float64,
            #                                         shape=[None], name='event%i_deltatime_ph'%event)
            #                                         for event in range(self._eventnum_batch)]

###########test placeholder###########################
            self.placeholders['event_nodes_eval_ph'] = tf.placeholder(tf.int32, shape=[None], name='event_eval_ph')

            self.placeholders['event_nodes_type_eval_ph'] = tf.placeholder(tf.int32, shape=[None], name='event_type_eval_ph')

            self.placeholders['event_nodes_history_eval_ph'] = tf.placeholder(tf.int32,
                                                        shape=[None, self._max_his_num, self._type_num], name='event_history_eval_ph')

            # self.placeholders['event_nodes_history_deltatime_eval_ph'] = tf.placeholder(tf.float64,
            #                                             shape=[None, self._max_his_num], name='event_history_deltatime_eval_ph')

            self.placeholders['event_partition_idx_eval_ph'] = tf.placeholder(tf.int32, shape=[self._num_node],
                                                            name='event_partition_idx_eval_ph')

            # self.placeholders['event_sub_eval_ph'] = tf.placeholder(tf.int32, shape=[None, self._type_num], name='event_sub_eval_ph')

            self.placeholders['negevent_nodes_eval_ph'] = tf.placeholder(tf.int32, shape=[None], name='negevent_eval_ph')

            self.placeholders['negevent_nodes_type_eval_ph'] = tf.placeholder(tf.int32, shape=[None], name='negevent_type_eval_ph')

            self.placeholders['negevent_nodes_history_eval_ph'] = tf.placeholder(tf.int32,
                                                shape=[None, self._max_his_num, self._type_num], name='negevent_history_eval_ph')
            #
            # self.placeholders['negevent_nodes_history_deltatime_eval_ph'] = tf.placeholder(tf.float64,
            #                                     shape=[None, self._max_his_num], name='negevent_history_deltatime_eval_ph')

            self.placeholders['has_neighbor_eval'] = tf.placeholder(tf.bool, shape=[None], name='hasneighbor_eval_ph')

            self.placeholders['has_neighbor_neg_eval'] = tf.placeholder(tf.bool, shape=[None], name='hasneighbor_neg_eval_ph')

            # self.placeholders['event_deltatime_eval_ph'] = tf.placeholder(tf.float64, shape=[None], name='event_deltatime_eval_ph')
######################################################

    def _create_variables(self):
        cur_seed = random.getrandbits(32)
        self._embedding_init = tf.get_variable('nodes_embedding_init', shape=[1, self._h_dim],
                                               dtype=tf.float64, trainable=True,
                                               initializer=tf.contrib.layers.xavier_initializer(uniform=False, seed=cur_seed))

        self._cellstates_init = tf.get_variable('nodes_cellstates_init', shape=[1, self._h_dim],
                                                dtype=tf.float64, trainable=True,
                                                initializer=tf.contrib.layers.xavier_initializer(uniform=False, seed=cur_seed))
                                                # initializer=tf.zeros_initializer())

        activation_name = self.params['graph_rnn_activation'].lower()
        if activation_name == 'tanh':
            self.activation_fun = tf.nn.tanh
        elif activation_name == 'relu':
            self.activation_fun = tf.nn.relu
        else:
            raise Exception("Unknown activation function type '%s'." % activation_name)

        if self._aggregator_type == 'mean':
            aggregator = MeanAggregator
        elif self._aggregator_type == 'attention':
            aggregator = AttentionAggregator2
        else:
            raise Exception('Unknown aggregator: ', self._aggregator_type)
        # self.weights['aggregator'] = aggregator(self._h_dim, keep=self._keep if self._istraining else 1.)
        self.weights['aggregator'] = aggregator(self._h_dim, keep=self.placeholders['keep_prob'], weight_decay=self._weight_decay)
        self.weights['type_weights_scalar'] = tf.Variable(tf.ones([self._type_num], dtype=tf.float64), trainable=True)
        self.weights['rnn_cells'] = {}
        if self.params['use_different_cell']:
            for node_type in range(self._type_num):
                cell = tf.nn.rnn_cell.LSTMCell(self._h_dim, activation=self.activation_fun, use_peepholes=True)
                if self._keep < 1.0:
                    cell = tf.nn.rnn_cell.DropoutWrapper(cell, input_keep_prob=self.placeholders['keep_prob'])
                self.weights['rnn_cells'][node_type] = cell
        else:
            cell = tf.nn.rnn_cell.LSTMCell(self._h_dim, activation=self.activation_fun, use_peepholes=True)
            if self._keep < 1.0:
                cell = tf.nn.rnn_cell.DropoutWrapper(cell, input_keep_prob=self.placeholders['keep_prob'])
            for node_type in range(self._type_num):
                self.weights['rnn_cells'][node_type] = cell

    def prepare_specific_graph_model(self):
        self._h_dim = self.params['hidden_size']
        self._type_num = self.params['node_type_numbers']
        self._eventnum_batch = self.params['batch_event_numbers']
        self._neg_num = self.params['negative_ratio']
        self._num_node_type = self.params['n_nodes_pertype']
        self._num_node = sum(self._num_node_type)
        self._sub_events_train, self._events_time_train = self.train_data.get_subevents()
        self._sub_events_valid, self._events_time_valid = self.valid_data.get_subevents()
        self._sub_events_test, self._events_time_test = self.test_data.get_subevents()
        self._max_his_num = self.params['max_his_num']
        self._his_type = self.params['his_type']
        self._keep = self.params['keep_prob']
        self._weight_decay = self.params['weight_decay']
        # self._istraining = self.params['is_training']
        self._aggregator_type = self.params['aggregator_type'].lower()
        self._ns = self.params['negative_sampling']
        if self._ns:
            print('negative sampling')
            self._neg_table_size = int(1e6)
            self._neg_sampling_power = 0.75
            self._neg_table = [np.zeros((self._neg_table_size,), dtype=np.int32) for _ in range(self._type_num)]
            self._init_neg_table()
        self._create_placeholders()
        self._create_variables()

    def build_specific_graph_model(self):
        def init_embedding():
            self._node_embedding_init = tf.tile(self._embedding_init, [self._num_node, 1])
            return self._node_embedding_init
        def init_cellstates():
            self._node_cellstates_init = tf.tile(self._cellstates_init, [self._num_node, 1])
            return self._node_cellstates_init
        def assign_embedding():
            return self.placeholders['nodes_embedding_ph']
        def assign_cellstates():
            return self.placeholders['nodes_cellstates_ph']

        node_vec = [None for _ in range(self._eventnum_batch + 1)]
        node_vec[0] = tf.cond(self.placeholders['is_init'], init_embedding, assign_embedding)
        node_cel = [None for _ in range(self._eventnum_batch + 1)]
        node_cel[0] = tf.cond(self.placeholders['is_init'], init_cellstates, assign_cellstates)
        # node_his = [None for _ in range(self._eventnum_batch + 1)]
        # node_his[0] = self.placeholders['nodes_history_ph']

        event_pred_list = []
        neg_event_pred_list = []
        self.triangularize_layer = Triangularize()
        self.attention_concat_layer = tf.layers.Dense(units=self._h_dim, use_bias=False,\
                                                kernel_regularizer=tf.contrib.layers.l2_regularizer(self._weight_decay))
        # self.reservior_predict_layer = Reservior_predict(output_dim=self._h_dim)
        for event_id in range(self._eventnum_batch):
            neg_event_states_stacked = [None for _ in range(self._neg_num)]
            node_vec_part = tf.dynamic_partition(node_vec[event_id],
                                                 self.placeholders['events_partition_idx_ph'][event_id],
                                                 self._type_num + 1)
            node_cel_part = tf.dynamic_partition(node_cel[event_id],
                                                 self.placeholders['events_partition_idx_ph'][event_id],
                                                 self._type_num + 1)
            dy_states = tf.nn.embedding_lookup(node_vec[event_id], self.placeholders['events_nodes_ph'][event_id])
            # his_events_index = tf.nn.embedding_lookup(node_his[event_id], self.placeholders['events_nodes_ph'][event_id])
            # his_events_states = tf.nn.embedding_lookup(node_vec[event_id], his_events_index)
            # his_events_deltatime = tf.nn.embedding_lookup(self.placeholders['nodes_history_deltatime_ph'], self.placeholders['events_nodes_ph'][event_id])
            his_events_states = tf.nn.embedding_lookup(node_vec[event_id], self.placeholders['events_nodes_history_ph'][event_id])
            # his_events_deltatime = self.placeholders['events_nodes_history_deltatime_ph'][event_id]
            his_events_states = tf.einsum('nmth,t->nmh', his_events_states, self.weights['type_weights_scalar'])
            his_states, index_score = self.weights['aggregator']((dy_states, his_events_states))
            hisconcat_states = tf.concat([dy_states, his_states], 1)
            hisconcat_states = self.attention_concat_layer(hisconcat_states)
            hisconcat_states = tf.where(self.placeholders['has_neighbor'][event_id], hisconcat_states, dy_states)
            _, _, type_count = tf.unique_with_counts(self.placeholders['events_nodes_type_ph'][event_id])
            event_weights = tf.nn.embedding_lookup(self.weights['type_weights_scalar'], self.placeholders['events_nodes_type_ph'][event_id])
            type_count = tf.cast(type_count, tf.float64)
            count_weights = tf.nn.embedding_lookup(tf.reciprocal(type_count),
                                                   self.placeholders['events_nodes_type_ph'][event_id])
            event_weights = tf.multiply(event_weights, count_weights)
            event_states = hisconcat_states*tf.expand_dims(event_weights, 1)
            send_states = dy_states*tf.expand_dims(event_weights, 1)
            send_states = tf.reduce_sum(send_states, axis=0, keepdims=True)
            for neg in range(self._neg_num):
                neg_dy_states = tf.nn.embedding_lookup(node_vec[event_id], self.placeholders['negevents_nodes_ph'][event_id][neg])
                # neg_his_events_index = tf.nn.embedding_lookup(node_his[event_id], self.placeholders['negevents_nodes_ph'][event_id][neg])
                # neg_his_events_states = tf.nn.embedding_lookup(node_vec[event_id], neg_his_events_index)
                # neg_his_events_deltatime = tf.nn.embedding_lookup(self.placeholders['nodes_history_deltatime_ph'], self.placeholders['negevents_nodes_ph'][event_id][neg])
                neg_his_events_states = tf.nn.embedding_lookup(node_vec[event_id], self.placeholders['negevents_nodes_history_ph'][event_id][neg])
                # neg_his_events_deltatime = self.placeholders['negevents_nodes_history_deltatime_ph'][event_id][neg]
                neg_his_events_states = tf.einsum('nmth,t->nmh', neg_his_events_states, self.weights['type_weights_scalar'])
                neg_his_states, _ = self.weights['aggregator']((neg_dy_states, neg_his_events_states))
                neg_hisconcat_states = tf.concat([neg_dy_states, neg_his_states], 1)
                neg_hisconcat_states = self.attention_concat_layer(neg_hisconcat_states)
                neg_hisconcat_states = tf.where(self.placeholders['has_neighbor_neg'][event_id][neg], neg_hisconcat_states, neg_dy_states)
                _, _, neg_type_count = tf.unique_with_counts(self.placeholders['negevents_nodes_type_ph'][event_id][neg])
                neg_event_weights = tf.nn.embedding_lookup(self.weights['type_weights_scalar'], self.placeholders['negevents_nodes_type_ph'][event_id][neg])
                neg_type_count = tf.cast(neg_type_count, tf.float64)
                neg_count_weights = tf.nn.embedding_lookup(tf.reciprocal(neg_type_count), self.placeholders['negevents_nodes_type_ph'][event_id][neg])
                neg_event_weights = tf.multiply(neg_event_weights, neg_count_weights)
                neg_event_states = neg_hisconcat_states*tf.expand_dims(neg_event_weights, 1)
                neg_event_states_stacked[neg] = neg_event_states
            new_target_embedding = [node_vec_part[0]]
            new_target_celstates = [node_cel_part[0]]
            # node_detatime_part = tf.dynamic_partition(self.placeholders['events_deltatime_ph'][event_id],
            #                                 self.placeholders['events_nodes_type_ph'][event_id], self._type_num)
            for node_type in range(self._type_num):
                target_embedding = node_vec_part[node_type+1]
                target_celstates = node_cel_part[node_type+1]
                # target_deltatime = tf.expand_dims(node_detatime_part[node_type], 1)
                # time_states = self.deltatime_layer(target_deltatime)
                send_states_pertype = tf.tile(send_states, [tf.shape(target_embedding)[0], 1])
                # send_states_pertype = tf.concat([send_states_pertype, time_states], 1)
                _, new_target_states_ch = self.weights['rnn_cells'][node_type](inputs=send_states_pertype,
                                                                    state=(target_celstates, target_embedding))
                new_target_celstates.append(new_target_states_ch[0])
                new_target_embedding.append(new_target_states_ch[1])
            condition_indices = tf.dynamic_partition(tf.range(self._num_node),
                                    self.placeholders['events_partition_idx_ph'][event_id], self._type_num+1)
            node_cel[event_id+1] = tf.dynamic_stitch(condition_indices, new_target_celstates)
            node_vec[event_id+1] = tf.dynamic_stitch(condition_indices, new_target_embedding)

        ######### change node his subevent
            # subevent_states = tf.nn.embedding_lookup(node_vec[event_id], self.placeholders['events_sub_ph'][event_id])
            # subevent_states = tf.einsum('nth,t->nh', subevent_states, self.weights['type_weights_scalar'])
            # reservior_score = self.reservior_predict_layer((dy_states, subevent_states))
            # bernoulli_dist = tf.distributions.Bernoulli(logits=reservior_score)
            # # samples_val = bernoulli_dist.sample(sample_shape=[tf.shape(dy_states)[0], tf.shape(subevent_states)[0]])
            # samples_val = bernoulli_dist.sample()
            # # samples_val.set_shape()
            # ranks = tf.contrib.framework.argsort(index_score, direction='ASCENDING')
            # min_mask = ranks < tf.expand_dims(tf.cast(tf.count_nonzero(samples_val, 1), tf.int32), 1)
            # # tf.where(min_index,  ,his_events_index)
            # min_index = tf.cast(tf.reshape(min_mask, [-1]), tf.int32)
            # partition_index = tf.where(self.placeholders['events_partition_idx_ph'][event_id] > 0,
            #         tf.ones_like(self.placeholders['events_partition_idx_ph'][event_id]), tf.zeros_like(self.placeholders['events_partition_idx_ph'][event_id]))
            # node_history_part = tf.dynamic_partition(node_his[event_id], partition_index, 2)
            # condition_indices_event = tf.dynamic_partition(tf.range(self._num_node), partition_index, 2)
            # # node_history_subpart = tf.dynamic_partition(node_history_part[1], tf.where(min_index, 1, 0), 2)
            # condition_indices_sub = tf.dynamic_partition(tf.range(tf.shape(min_index)[0]), min_index, 2)
            # node_history_subpart = tf.dynamic_partition(tf.reshape(node_history_part[1], [-1, self._type_num]), min_index, 2)
            # samples_mask = tf.cast(samples_val, tf.bool)
            # samples_subevent = tf.expand_dims(self.placeholders['events_sub_ph'][event_id], 0)
            # # print(samples_val)
            # # print(samples_mask.get_shape().ndims)
            # samples_subevent = tf.boolean_mask(tf.tile(samples_subevent, [tf.shape(self.placeholders['events_nodes_ph'][event_id])[0],1,1]), samples_mask)
            # node_sub = tf.reshape(tf.dynamic_stitch(condition_indices_sub, [node_history_subpart[0], samples_subevent]), tf.shape(node_history_part[1]))
            # node_his[event_id+1] = tf.dynamic_stitch(condition_indices_event, [node_history_part[0], node_sub])
        ################################

            # tf.while_loop(should_continue, stitch_iteration)
            # tf.nn.top_k(index_score, tf.count_nonzero(samples_val, 1))

            # node_history_index = tf.stack([self.placeholders['events_nodes_ph'][event_id], min_index], axis=1)
            # node_history_ph = tf.scatter_update(self.placeholders['nodes_history_ph'], node_history_index, )
        # ###pairwise layer to predict
            event_scores = tf.expand_dims(event_states, 0)
            event_scores_h = tf.matmul(event_scores, event_scores, transpose_b=True)
            event_scores_h = self.triangularize_layer(event_scores_h)
            event_scores_h = tf.layers.flatten(event_scores_h)
            y_pred = tf.reduce_sum(event_scores_h, 1)
            neg_event_scores = tf.stack(neg_event_states_stacked)
            neg_event_scores_h = tf.matmul(neg_event_scores, neg_event_scores, transpose_b=True)
            neg_event_scores_h = self.triangularize_layer(neg_event_scores_h)
            neg_event_scores_h = tf.layers.flatten(neg_event_scores_h)
            neg_y_pred = tf.reduce_sum(neg_event_scores_h, 1)
            event_pred_list.append(y_pred)
            neg_event_pred_list.append(neg_y_pred)
        pred = tf.squeeze(tf.stack(event_pred_list))
        neg_pred = tf.squeeze(tf.stack(neg_event_pred_list))
        event_losses = tf.nn.sigmoid_cross_entropy_with_logits(labels=tf.ones_like(pred), logits=pred)
        neg_event_losses = tf.nn.sigmoid_cross_entropy_with_logits(labels=tf.zeros_like(neg_pred), logits=neg_pred)
        loss_mean = (tf.reduce_sum(event_losses) + tf.reduce_sum(neg_event_losses)) / self._eventnum_batch
        # l2_loss = tf.losses.get_regularization_loss()
        # loss_mean += l2_loss
        # loss = tf.log(tf.sigmoid(pred)) + tf.reduce_sum(tf.log(tf.sigmoid(-neg_pred)), 1)
        # loss_mean = -tf.reduce_mean(loss)
        predict = tf.sigmoid(pred)
        neg_predict = tf.sigmoid(neg_pred)
        return loss_mean, node_vec[event_id+1], node_cel[event_id+1], predict, neg_predict

    def build_specific_eval_graph_model(self):
        node_vec = self.placeholders['nodes_embedding_ph']
        node_cel = self.placeholders['nodes_cellstates_ph']
        # node_his = self.placeholders['nodes_history_ph']

        # node_vec = tf.where(self.placeholders['is_init'], self._embedding_init, self.placeholders['nodes_embedding_ph'])
        # node_cel = tf.where(self.placeholders['is_init'], self._cellstates_init, self.placeholders['nodes_cellstates_ph'])

        node_vec_part = tf.dynamic_partition(node_vec, self.placeholders['event_partition_idx_eval_ph'], self._type_num + 1)
        node_cel_part = tf.dynamic_partition(node_cel, self.placeholders['event_partition_idx_eval_ph'], self._type_num + 1)
        dy_states = tf.nn.embedding_lookup(node_vec, self.placeholders['event_nodes_eval_ph'])
        his_events_states = tf.nn.embedding_lookup(node_vec, self.placeholders['event_nodes_history_eval_ph'])
        # his_events_deltatime = self.placeholders['event_nodes_history_deltatime_eval_ph']
        # his_events_states = tf.einsum('nmth,t->nmh', his_events_states, self.weights['type_weights_scalar'])
        # his_states = self.weights['aggregator']((dy_states, his_events_states, his_events_deltatime))
        # his_states = self.weights['aggregator']((dy_states, his_events_states))
        # hisconcat_states = tf.nn.dropout(tf.concat([dy_states, his_states], 1), self.placeholders['keep_prob'])
        # his_events_index = tf.nn.embedding_lookup(node_his, self.placeholders['event_nodes_eval_ph'])
        # his_events_states = tf.nn.embedding_lookup(node_vec, his_events_index)
        his_events_states = tf.einsum('nmth,t->nmh', his_events_states, self.weights['type_weights_scalar'])
        his_states, index_score = self.weights['aggregator']((dy_states, his_events_states))
        #his_states
        hisconcat_states = tf.concat([dy_states, his_states], 1)
        hisconcat_states = self.attention_concat_layer(hisconcat_states)
        hisconcat_states = tf.where(self.placeholders['has_neighbor_eval'], hisconcat_states, dy_states)
        _, _, type_count = tf.unique_with_counts(self.placeholders['event_nodes_type_eval_ph'])
        event_weights = tf.nn.embedding_lookup(self.weights['type_weights_scalar'], self.placeholders['event_nodes_type_eval_ph'])
        type_count = tf.cast(type_count, tf.float64)
        count_weights = tf.nn.embedding_lookup(tf.reciprocal(type_count),
                                               self.placeholders['event_nodes_type_eval_ph'])
        event_weights = tf.multiply(event_weights, count_weights)
        event_states = hisconcat_states * tf.expand_dims(event_weights, 1)
        send_states = dy_states*tf.expand_dims(event_weights, 1)
        send_states = tf.reduce_sum(send_states, axis=0, keepdims=True)
        neg_dy_states = tf.nn.embedding_lookup(node_vec, self.placeholders['negevent_nodes_eval_ph'])
        neg_his_events_states = tf.nn.embedding_lookup(node_vec, self.placeholders['negevent_nodes_history_eval_ph'])
        # neg_his_events_deltatime = self.placeholders['negevent_nodes_history_deltatime_eval_ph']
        # neg_his_events_states = tf.einsum('nmth,t->nmh', neg_his_events_states, self.weights['type_weights_scalar'])
        # neg_his_states = self.weights['aggregator']((neg_dy_states, neg_his_events_states, neg_his_events_deltatime))
        # neg_his_states = self.weights['aggregator']((neg_dy_states, neg_his_events_states))
        # neg_hisconcat_states = tf.nn.dropout(tf.concat([neg_dy_states, neg_his_states], 1), self.placeholders['keep_prob'])

        #neg_his_states
        # neg_his_events_index = tf.nn.embedding_lookup(node_his, self.placeholders['negevent_nodes_eval_ph'])
        # neg_his_events_states = tf.nn.embedding_lookup(node_vec, neg_his_events_index)
        neg_his_events_states = tf.einsum('nmth,t->nmh', neg_his_events_states, self.weights['type_weights_scalar'])
        neg_his_states, _ = self.weights['aggregator']((neg_dy_states, neg_his_events_states))
        neg_hisconcat_states = tf.concat([neg_dy_states, neg_his_states], 1)
        neg_hisconcat_states = self.attention_concat_layer(neg_hisconcat_states)
        neg_hisconcat_states = tf.where(self.placeholders['has_neighbor_neg_eval'], neg_hisconcat_states, neg_dy_states)
        _, _, neg_type_count = tf.unique_with_counts(self.placeholders['negevent_nodes_type_eval_ph'])
        neg_event_weights = tf.nn.embedding_lookup(self.weights['type_weights_scalar'], self.placeholders['negevent_nodes_type_eval_ph'])
        neg_type_count = tf.cast(neg_type_count, tf.float64)
        neg_count_weights = tf.nn.embedding_lookup(tf.reciprocal(neg_type_count),
                                                   self.placeholders['negevent_nodes_type_eval_ph'])
        neg_event_weights = tf.multiply(neg_event_weights, neg_count_weights)
        neg_event_states = neg_hisconcat_states * tf.expand_dims(neg_event_weights, 1)
        new_target_embedding = [node_vec_part[0]]
        new_target_celstates = [node_cel_part[0]]
        # node_detatime_part = tf.dynamic_partition(self.placeholders['event_deltatime_eval_ph'],
        #                                     self.placeholders['event_nodes_type_eval_ph'], self._type_num)
        for node_type in range(self._type_num):
            target_embedding = node_vec_part[node_type+1]
            target_celstates = node_cel_part[node_type+1]
            # target_deltatime = tf.expand_dims(node_detatime_part[node_type], 1)
            # time_states = self.deltatime_layer(target_deltatime)
            send_states_pertype = tf.tile(send_states, [tf.shape(target_embedding)[0], 1])
            # send_states_pertype = tf.concat([send_states_pertype, time_states], 1)
            _, new_target_states_ch = self.weights['rnn_cells'][node_type](inputs=send_states_pertype,
                                                            state=(target_celstates, target_embedding))
            new_target_celstates.append(new_target_states_ch[0])
            new_target_embedding.append(new_target_states_ch[1])
        condition_indices = tf.dynamic_partition(tf.range(self._num_node),
                                                 self.placeholders['event_partition_idx_eval_ph'],
                                                 self._type_num + 1)
        node_cel = tf.dynamic_stitch(condition_indices, new_target_celstates)
        node_vec = tf.dynamic_stitch(condition_indices, new_target_embedding)

        ######### change node his subevent
        # subevent_states = tf.nn.embedding_lookup(node_vec, self.placeholders['event_sub_eval_ph'])
        # subevent_states = tf.einsum('nth,t->nh', subevent_states, self.weights['type_weights_scalar'])
        # reservior_score = self.reservior_predict_layer((dy_states, subevent_states))
        # bernoulli_dist = tf.distributions.Bernoulli(logits=reservior_score)
        # samples_val = bernoulli_dist.sample()
        # ranks = tf.contrib.framework.argsort(index_score, direction='ASCENDING')
        # min_mask = ranks < tf.expand_dims(tf.cast(tf.count_nonzero(samples_val, 1), tf.int32), 1)
        # min_index = tf.cast(tf.reshape(min_mask, [-1]), tf.int32)
        # partition_index = tf.where(self.placeholders['event_partition_idx_eval_ph'] > 0,
        #                            tf.ones_like(self.placeholders['event_partition_idx_eval_ph']),
        #                            tf.zeros_like(self.placeholders['event_partition_idx_eval_ph']))
        # node_history_part = tf.dynamic_partition(node_his, partition_index, 2)
        # condition_indices_event = tf.dynamic_partition(tf.range(self._num_node), partition_index, 2)
        # condition_indices_sub = tf.dynamic_partition(tf.range(tf.shape(min_index)[0]), min_index, 2)
        # node_history_subpart = tf.dynamic_partition(tf.reshape(node_history_part[1], [-1, self._type_num]), min_index, 2)
        # samples_mask = tf.cast(samples_val, tf.bool)
        # samples_subevent = tf.expand_dims(self.placeholders['event_sub_eval_ph'], 0)
        # samples_subevent = tf.boolean_mask(tf.tile(samples_subevent, [tf.shape(self.placeholders['event_nodes_eval_ph'])[0], 1, 1]), samples_mask)
        # node_sub = tf.reshape(tf.dynamic_stitch(condition_indices_sub, [node_history_subpart[0], samples_subevent]),
        #                       tf.shape(node_history_part[1]))
        # node_his = tf.dynamic_stitch(condition_indices_event, [node_history_part[0], node_sub])
        ################################
        ###pairwise layer to predict
        event_scores = event_states
        neg_event_scores = neg_event_states
        event_scores = tf.expand_dims(event_scores, 0)
        neg_event_scores = tf.expand_dims(neg_event_scores, 0)
        event_scores_h = tf.matmul(event_scores, event_scores, transpose_b=True)
        event_scores_h = self.triangularize_layer(event_scores_h)
        event_scores_h = tf.layers.flatten(event_scores_h)
        y_pred = tf.reduce_sum(event_scores_h, 1, keepdims=True)
        neg_event_scores_h = tf.matmul(neg_event_scores, neg_event_scores, transpose_b=True)
        neg_event_scores_h = self.triangularize_layer(neg_event_scores_h)
        neg_event_scores_h = tf.layers.flatten(neg_event_scores_h)
        neg_y_pred = tf.reduce_sum(neg_event_scores_h, 1, keepdims=True)
        event_losses = tf.nn.sigmoid_cross_entropy_with_logits(labels=tf.ones_like(y_pred), logits=y_pred)
        neg_event_losses = tf.nn.sigmoid_cross_entropy_with_logits(labels=tf.zeros_like(neg_y_pred), logits=neg_y_pred)
        loss_mean = tf.reduce_sum(event_losses) + tf.reduce_sum(neg_event_losses)
        # l2_loss = tf.losses.get_regularization_loss()
        # loss_mean += l2_loss

        # loss = tf.log(tf.sigmoid(y_pred)) + tf.log(tf.sigmoid(-neg_y_pred))
        # loss_mean = -tf.reduce_mean(loss)

        predict = tf.sigmoid(tf.squeeze(y_pred))
        neg_predict = tf.sigmoid(tf.squeeze(neg_y_pred))
        return loss_mean, node_vec, node_cel, predict, neg_predict

    def train(self):
        best_loss = 100.0
        best_epoch = -1
        with open(self.log_file, 'w') as log_out:
            for epoch in range(self.params['num_epochs']):
                epoch_loss = []
                self.node_embedding_cur = np.zeros([self._num_node, self._h_dim], dtype=np.float64)
                self.node_cellstates_cur = np.zeros([self._num_node, self._h_dim], dtype=np.float64)
                # self.is_init = [True for _ in range(self._num_node)]
                self.node_his_event = {node:[] for node in range(self._num_node)}
                self.has_neighbor = [False for _ in range(self._num_node)]
                # self.node_his_event = self.get_node_his_event_init()
                self.train_data.batch_size = self._eventnum_batch
                train_batches_num = self.train_data.get_batch_num()
                print('batches'+str(train_batches_num))
                is_init = True
                epoch_flag = False
                print('start epoch %i'%(epoch))
                while not epoch_flag:
                    batch_feed_dict, epoch_flag = self.get_batch_feed_dict('train', is_init)
                    # batch_feed_dict, epoch_flag = self.get_batch_feed_dict('train')
                    fetches = [self.ops['loss'], self.ops['node_vec'], self.ops['node_cel'],\
                               self.ops['global_step'], self.ops['lr'], self.ops['train_op']]
                    cost, self.node_embedding_cur, self.node_cellstates_cur, step, lr, _ =\
                        self.sess.run(fetches, feed_dict=batch_feed_dict)
                    epoch_loss.append(cost)
                    is_init = False
                    if np.isnan(cost):
                        log_out.write('Train ' + str(epoch) + ':Nan error!\n')
                        print('Train ' + str(epoch) + ':Nan error!')
                        return
                    if step == 1 or step % (self.params['decay_step']/10) == 0:
                        avgc = np.mean(epoch_loss)
                        log_out.write('Epoch {}\tStep {}\tlr: {:.6f}\tcost:{:.6f}\tavgc:{:.6f}\n'.format(epoch, step, lr, cost, avgc))
                        print('Epoch {}\tStep {}\tlr: {:.6f}\tcost:{:.6f}\tavgc:{:.6f}'.format(epoch, step, lr, cost, avgc))
                        sys.stdout.flush()
                        log_out.flush()
                node_embedding_until_train = copy.deepcopy(self.node_embedding_cur)
                node_cellstates_until_train = copy.deepcopy(self.node_cellstates_cur)
                print('start valid')
                valid_loss = self.validation(log_out)
                log_out.write('Evaluation loss after step {}: {:.6f}\n'.format(step, valid_loss))
                print('Evaluation loss after step {}: {:.6f}'.format(step, valid_loss))
                print('start test')
                self.test(log_out)
                if valid_loss < best_loss:
                    best_epoch = epoch
                    best_loss = valid_loss
                    ckpt_path = os.path.join(self.checkpoint_dir, 'model.ckpt')
                    self.saver.save(self.sess, ckpt_path, global_step=step)
                    embedding_path = self.checkpoint_dir + '_embedding.npy'
                    cellstates_path = self.checkpoint_dir + '_cellstates.npy'
                    np.save(embedding_path, node_embedding_until_train)
                    np.save(cellstates_path, node_cellstates_until_train)
                    print('model saved to {}'.format(ckpt_path))
                    log_out.write('model saved to {}\n'.format(ckpt_path))
                    sys.stdout.flush()
                if epoch-best_epoch >= self.params['patience']:
                    log_out.write('Stopping training after %i epochs without improvement on validation.\n' % self.params['patience'])
                    print('Stopping training after %i epochs without improvement on validation.' % self.params['patience'])
                    break
            log_out.write('Best evaluation loss appears in epoch {}. Lowest loss: {:.6f}\n'.format(best_epoch, best_loss))
            print('Best evaluation loss appears in epoch {}. Lowest loss: {:.6f}'.format(best_epoch, best_loss))

    def validation(self, log_out):
        epoch_flag = False
        is_init = False
        valid_loss = []
        self.valid_data.batch_size = self._eventnum_batch
        valid_batches_num = self.valid_data.get_batch_num()
        print('valid nums:' + str(valid_batches_num))
        log_out.write('valid nums:\n' + str(valid_batches_num))
        labels = []
        val_preds = []
        while not epoch_flag:
            fetches = [self.ops['loss'], self.ops['node_vec'], self.ops['node_cel'],\
                       self.ops['pred'], self.ops['neg_pred']]
            feed_dict_valid, epoch_flag = self.get_batch_feed_dict('valid', is_init)
            # feed_dict_valid, epoch_flag = self.get_batch_feed_dict('valid')
            cost, self.node_embedding_cur, self.node_cellstates_cur, pred, neg_pred = self.sess.run(fetches, feed_dict=feed_dict_valid)
            print(cost)
            log_out.write('cost:{:.6f}\n'.format(cost))
            valid_loss.append(cost)
            val_preds.extend(list(pred))
            # for row in range(self._eventnum_batch):
            #     neg_pred_set = list(neg_pred[row,:])
            #     val_preds.append(random.choice(neg_pred_set))
            if self._neg_num == 1:
                val_preds.extend(list(neg_pred))
            else:
                val_preds.extend(list(neg_pred[:,0]))
            labels.extend([1 for _ in range(self._eventnum_batch)])
            labels.extend([0 for _ in range(self._eventnum_batch)])
        mae = metrics.mean_absolute_error(labels, val_preds)
        rmse = np.sqrt(metrics.mean_squared_error(labels, val_preds))
        fpr, tpr, thresholds = metrics.roc_curve(labels, val_preds, pos_label=1)
        auc = metrics.auc(fpr, tpr)
        ap = metrics.average_precision_score(labels, val_preds)
        print('mae:%f, rmse:%f, auc:%f, ap:%f' % (mae, rmse, auc, ap))
        log_out.write('mae:{:.6f}\trmse:{:.6f}\tauc:{:.6f}\tap:{:.6f}\n'.format(mae, rmse, auc, ap))
        return np.mean(valid_loss)


    def test(self, log_out):
        self.test_data.batch_size = 1
        test_batches_num = self.test_data.get_batch_num()
        print('test nums:'+str(test_batches_num))
        log_out.write('test nums:\n' + str(test_batches_num))
        epoch_flag = False
        val_preds = []
        labels = []
        test_loss = []
        is_init = False
        while not epoch_flag:
            fetches = [self.ops['loss_eval'], self.ops['node_vec_eval'], self.ops['node_cel_eval'],\
                self.ops['predict'], self.ops['neg_predict']]
            feed_dict_test, epoch_flag = self.get_feed_dict_eval(is_init)
            # feed_dict_test, epoch_flag = self.get_feed_dict_eval()
            cost, self.node_embedding_cur, self.node_cellstates_cur, predict, neg_predict = \
                self.sess.run(fetches, feed_dict=feed_dict_test)
            val_preds.append(predict)
            val_preds.append(neg_predict)
            test_loss.append(cost)
            labels.append(1)
            labels.append(0)
        print('label')
        print(labels[:10])
        print('pred')
        print(val_preds[:10])
        mae = metrics.mean_absolute_error(labels, val_preds)
        rmse = np.sqrt(metrics.mean_squared_error(labels, val_preds))
        fpr, tpr, thresholds = metrics.roc_curve(labels, val_preds, pos_label=1)
        auc = metrics.auc(fpr, tpr)
        # auc = metrics.roc_auc_score(labels, val_preds)
        ap = metrics.average_precision_score(labels, val_preds)
        print('mae:%f, rmse:%f, auc:%f, ap:%f' % (mae, rmse, auc, ap))
        log_out.write('mae:{:.6f}\trmse:{:.6f}\tauc:{:.6f}\tap:{:.6f}\n'.format(mae, rmse, auc, ap))
        print('test cost%f'%(np.mean(test_loss)))
        log_out.write('test cost:{:.6f}\n'.format(np.mean(test_loss)))

    # def sample_negbatch_events(self, batch_data, neg_num):
    #     batch_data_neg_list = []
    #     for event in range(len(batch_data)):
    #         data_neg = [[[] for _ in range(self._type_num+3)] for _ in range(neg_num)]
    #         for neg in range(neg_num):
    #             # neg_type = random.choice(range(self._type_num))
    #             for type in range(self._type_num):
    #                 # if neg_type == type:
    #                 if True:
    #                     prenum = 0
    #                     for pretype in range(type):
    #                         prenum += self._num_node_type[pretype]
    #                     while (len(data_neg[neg][type]) < len(batch_data[event][type])):
    #                         neg_node = random.randint(prenum, prenum+self._num_node_type[type] - 1)
    #                         if (neg_node in data_neg[neg][type]) or (neg_node in batch_data[event][type]):
    #                             continue
    #                         data_neg[neg][type].append(neg_node)
    #                 else:
    #                     data_neg[neg][type] = batch_data[event][type]
    #             data_neg[neg][-1] = batch_data[event][-1]
    #             data_neg[neg][-2] = batch_data[event][-2]
    #             data_neg[neg][-3] = batch_data[event][-3]
    #         batch_data_neg_list.append(data_neg)
    #     return batch_data_neg_list

    #### last new
    def sample_negbatch_events_withns(self, batch_data, neg_num):
        batch_data_neg_list = []
        for event in range(len(batch_data)):
            data_neg = [[[] for _ in range(self._type_num+3)] for _ in range(neg_num)]
            for neg in range(neg_num):
                neg_type = random.choice(range(self._type_num))
                # neg_type = 0
                for type in range(self._type_num):
                    if neg_type == type:
                        data_neg[neg][type] = self.negative_sampling(neg_type, len(batch_data[event][type]))
                        # replace_node = random.choice(batch_data[event][type])
                        # for node in batch_data[event][type]:
                        #     if replace_node == node:
                        #     # if True:
                        #         while True:
                        #             # prenum = 0
                        #             # for pretype in range(type):
                        #             #     prenum += self._num_node_type[pretype]
                        #             # neg_node = random.randint(prenum, prenum+self._num_node_type[type] - 1)
                        #             neg_node = self.negative_sampling(neg_type, 1)[0]
                        #             if neg_node in batch_data[event][type]:
                        #                 continue
                        #             else:
                        #                 data_neg[neg][type].append(neg_node)
                        #                 break
                        #     else:
                        #         data_neg[neg][type].append(node)
                    else:
                        data_neg[neg][type] = batch_data[event][type]
                data_neg[neg][-1] = batch_data[event][-1]
                data_neg[neg][-2] = batch_data[event][-2]
                data_neg[neg][-3] = batch_data[event][-3]
            batch_data_neg_list.append(data_neg)
        return batch_data_neg_list

    # def sample_negbatch_events_withns(self, batch_data, neg_num):
    #     batch_data_neg_list = []
    #     for event in range(len(batch_data)):
    #         data_neg = [[[] for _ in range(self._type_num+3)] for _ in range(neg_num)]
    #         for neg in range(neg_num):
    #             neg_type = random.choice(range(self._type_num))
    #             replace_node = random.choice(batch_data[event][neg_type])
    #             for type in range(self._type_num):
    #                 if neg_type == type:
    #                     # data_neg[neg][type] = self.negative_sampling(neg_type, len(batch_data[event][type]))
    #                     for node in batch_data[event][type]:
    #                         # if True:
    #                         if replace_node == node:
    #                             while True:
    #                         #         # prenum = 0
    #                         #         # for pretype in range(type):
    #                         #         #     prenum += self._num_node_type[pretype]
    #                         #         # neg_node = random.randint(prenum, prenum+self._num_node_type[type] - 1)
    #                                 neg_node = self.negative_sampling(neg_type, 1)[0]
    #                                 if neg_node in batch_data[event][type]:
    #                                     continue
    #                                 else:
    #                                     data_neg[neg][type].append(neg_node)
    #                                     break
    #                         else:
    #                             data_neg[neg][type].append(node)
    #                 else:
    #                     data_neg[neg][type] = batch_data[event][type]
    #             data_neg[neg][-1] = batch_data[event][-1]
    #             data_neg[neg][-2] = batch_data[event][-2]
    #             data_neg[neg][-3] = batch_data[event][-3]
    #         batch_data_neg_list.append(data_neg)
    #     return batch_data_neg_list

    # # changed from this old last new
    def sample_negbatch_events(self, batch_data, neg_num):
        batch_data_neg_list = []
        for event in range(len(batch_data)):
            data_neg = [[[] for _ in range(self._type_num+3)] for _ in range(neg_num)]
            for neg in range(neg_num):
                neg_type = random.choice(range(self._type_num))
                # neg_type = 0
                for type in range(self._type_num):
                    if neg_type == type:
                        # replace_node = random.choice(batch_data[event][type])
                        # for node in batch_data[event][type]:
                        #     if replace_node == node:
                        #     # if True:
                        #         while True:
                        #             prenum = 0
                        #             for pretype in range(type):
                        #                 prenum += self._num_node_type[pretype]
                        #             neg_node = random.randint(prenum, prenum+self._num_node_type[type] - 1)
                        #             if neg_node in batch_data[event][type]:
                        #                 continue
                        #             else:
                        #                 data_neg[neg][type].append(neg_node)
                        #                 break
                        #     else:
                        #         data_neg[neg][type].append(node)
                        prenum = 0
                        for pretype in range(type):
                            prenum += self._num_node_type[pretype]
                        data_neg[neg][type] = list(np.random.randint(prenum, prenum+self._num_node_type[type]-1, len(batch_data[event][type])))
                    else:
                        data_neg[neg][type] = batch_data[event][type]
                data_neg[neg][-1] = batch_data[event][-1]
                data_neg[neg][-2] = batch_data[event][-2]
                data_neg[neg][-3] = batch_data[event][-3]
            batch_data_neg_list.append(data_neg)
        return batch_data_neg_list


    # # changed from this old last new
    # def sample_negbatch_events(self, batch_data, neg_num):
    #     batch_data_neg_list = []
    #     for event in range(len(batch_data)):
    #         data_neg = [[[] for _ in range(self._type_num+3)] for _ in range(neg_num)]
    #         for neg in range(neg_num):
    #             neg_type = random.choice(range(self._type_num))
    #             replace_node = random.choice(batch_data[event][neg_type])
    #             prenum = 0
    #             for pretype in range(neg_type):
    #                 prenum += self._num_node_type[pretype]
    #             for type in range(self._type_num):
    #                 if neg_type == type:
    #                     # replace_node = random.choice(batch_data[event][type])
    #                     for node in batch_data[event][type]:
    #                         # if True:
    #                         if replace_node == node:
    #                             while True:
    #                                 neg_node = random.randint(prenum, prenum+self._num_node_type[type] - 1)
    #                                 if neg_node in batch_data[event][type]:
    #                                     continue
    #                                 else:
    #                                     data_neg[neg][type].append(neg_node)
    #                                     break
    #                         else:
    #                             data_neg[neg][type].append(node)
    #                     # prenum = 0
    #                     # for pretype in range(type):
    #                     #     prenum += self._num_node_type[pretype]
    #                     # data_neg[neg][type] = list(np.random.randint(prenum, prenum+self._num_node_type[type]-1, len(batch_data[event][type])))
    #                 else:
    #                     data_neg[neg][type] = batch_data[event][type]
    #             data_neg[neg][-1] = batch_data[event][-1]
    #             data_neg[neg][-2] = batch_data[event][-2]
    #             data_neg[neg][-3] = batch_data[event][-3]
    #         batch_data_neg_list.append(data_neg)
    #     return batch_data_neg_list

    ##new
    # def sample_negbatch_events(self, batch_data, neg_num_pertype):
    #     batch_data_neg_list = []
    #     for event in range(len(batch_data)):
    #         data_neg = [[[] for _ in range(self._type_num+3)] for _ in range(self._type_num*neg_num_pertype)]
    #         for neg_type in range(self._type_num):
    #             for neg in range(neg_num_pertype):
    #                 for type in range(self._type_num):
    #                     if neg_type == type:
    #                         replace_node = random.choice(batch_data[event][type])
    #                         for node in batch_data[event][type]:
    #                             if replace_node == node:
    #                                 while True:
    #                                     prenum = 0
    #                                     for pretype in range(type):
    #                                         prenum += self._num_node_type[pretype]
    #                                     neg_node = random.randint(prenum, prenum+self._num_node_type[type] - 1)
    #                                     if neg_node in batch_data[event][type]:
    #                                         continue
    #                                     else:
    #                                         data_neg[neg_type*neg_num_pertype+neg][type].append(neg_node)
    #                                         break
    #                             else:
    #                                 data_neg[neg_type*neg_num_pertype+neg][type].append(node)
    #                     else:
    #                         data_neg[neg_type*neg_num_pertype+neg][type] = batch_data[event][type]
    #                 data_neg[neg_type*neg_num_pertype+neg][-1] = batch_data[event][-1]
    #                 data_neg[neg_type*neg_num_pertype+neg][-2] = batch_data[event][-2]
    #                 data_neg[neg_type*neg_num_pertype+neg][-3] = batch_data[event][-3]
    #         batch_data_neg_list.append(data_neg)
    #     return batch_data_neg_list

    # def sample_negbatch_events(self, batch_data, neg_num):
    #     batch_data_neg_list = []
    #     for event in range(len(batch_data)):
    #         data_neg = [[[] for _ in range(self._type_num+3)] for _ in range(neg_num)]
    #         for neg in range(neg_num):
    #             neg_type = random.choice(range(self._type_num))
    #             for type in range(self._type_num):
    #                 if neg_type == type:
    #                     replace_node = random.choice(batch_data[event][type])
    #                     for node in batch_data[event][type]:
    #                         if replace_node == node:
    #                         # if True:
    #                             while True:
    #                                 prenum = 0
    #                                 for pretype in range(type):
    #                                     prenum += self._num_node_type[pretype]
    #                                 neg_node = random.randint(prenum, prenum+self._num_node_type[type] - 1)
    #                                 if neg_node in batch_data[event][type]:
    #                                     continue
    #                                 else:
    #                                     data_neg[neg][type].append(neg_node)
    #                                     break
    #                         else:
    #                             data_neg[neg][type].append(node)
    #                 else:
    #                     data_neg[neg][type] = batch_data[event][type]
    #             data_neg[neg][-1] = batch_data[event][-1]
    #             data_neg[neg][-2] = batch_data[event][-2]
    #             data_neg[neg][-3] = batch_data[event][-3]
    #         batch_data_neg_list.append(data_neg)
    #     return batch_data_neg_list



    def sample_subevent_fromhis(self, event_data, node_his_event, sub_events_list, events_time_list, his_type):
        if his_type == 'random':
            return self.sample_subevent_fromhis_random(event_data, node_his_event, sub_events_list, events_time_list)
        elif his_type == 'last':
            return self.sample_subevent_fromhis_last(event_data, node_his_event, sub_events_list, events_time_list)
        else:
            print('history type wrong')

    # sample last subevent
    def sample_subevent_fromhis_last(self, event_data, node_his_event, sub_events_list, events_time_list):
        type_data = []
        for node_type in range(self._type_num):
            type_data.extend(event_data[node_type])
        sampled_his_event = [[] for _ in range(len(type_data))]
        isneighbor = [True for _ in range(len(type_data))]
        event_deltatime = [0.0 for _ in range(len(type_data))]
        his_event_deltatime = [[] for _ in range(len(type_data))]
        for node_index in range(len(type_data)):
            his_len = len(node_his_event[type_data[node_index]])
            if his_len == 0:
                sub_his_event = []
                sub_his_event_deltatime = []
                sub_events = event_data[-2]
                while len(sub_his_event)<self._max_his_num:
                    if len(sub_his_event)+len(sub_events)<self._max_his_num:
                        sub_his_event.extend(sub_events)
                        sub_his_event_deltatime.extend([0]*len(sub_events))
                    elif len(sub_his_event)+len(sub_events)==self._max_his_num:
                        sub_his_event.extend(sub_events)
                        sub_his_event_deltatime.extend([0]*len(sub_events))
                        break
                    else:
                        extra = self._max_his_num - len(sub_his_event)
                        # sub_his_event.extend(sub_events[:-extra])
                        selected_index = random.sample(range(len(sub_events)), extra)
                        sub_his_event.extend([sub_events[i] for i in selected_index])
                        sub_his_event_deltatime.extend([0]*extra)
                        break
                sampled_his_event[node_index] = sub_his_event
                his_event_deltatime[node_index] = sub_his_event_deltatime
                isneighbor[node_index] = False
                event_deltatime[node_index] = 0.0
            else:
                sub_his_event = []
                sub_his_event_deltatime = []
                sub_selected_hisevent = []
                sub_selected_hisdeltatime = []
                event_his = node_his_event[type_data[node_index]]
                event_time = event_data[-3]
                for his_index in range(len(event_his)):
                    sub_events = sub_events_list[event_his[his_index]]
                    his_event_time = events_time_list[event_his[his_index]]
                    sub_his_event.extend(sub_events)
                    sub_his_event_deltatime.extend([event_time-his_event_time]*len(sub_events))
                while len(sub_selected_hisevent)<self._max_his_num:
                    extra = self._max_his_num - len(sub_selected_hisevent)
                    if extra>len(sub_his_event):
                        sub_selected_hisevent.extend(sub_his_event)
                        sub_selected_hisdeltatime.extend(sub_his_event_deltatime)
                    else:
                        # selected_index = random.sample(range(len(sub_his_event)), extra)
                        # sub_selected_hisevent.extend([sub_his_event[i] for i in selected_index])
                        # sub_selected_hisdeltatime.extend([sub_his_event_deltatime[i] for i in selected_index])
                        sub_selected_hisevent.extend(sub_his_event[-extra:])
                        sub_selected_hisdeltatime.extend(sub_his_event_deltatime[-extra:])
                sampled_his_event[node_index] = sub_selected_hisevent
                his_event_deltatime[node_index] = sub_selected_hisdeltatime
                isneighbor[node_index] = True
                event_deltatime[node_index] = event_time-events_time_list[event_his[-1]]
        return sampled_his_event, his_event_deltatime, isneighbor, event_deltatime

    # random sample subevent
    def sample_subevent_fromhis_random(self, event_data, node_his_event, sub_events_list, events_time_list):
        type_data = []
        for node_type in range(self._type_num):
            type_data.extend(event_data[node_type])
        sampled_his_event = [[] for _ in range(len(type_data))]
        isneighbor = [True for _ in range(len(type_data))]
        event_deltatime = [0.0 for _ in range(len(type_data))]
        his_event_deltatime = [[] for _ in range(len(type_data))]
        for node_index in range(len(type_data)):
            his_len = len(node_his_event[type_data[node_index]])
            if his_len == 0:
                sub_his_event = []
                sub_his_event_deltatime = []
                sub_events = event_data[-2]
                while len(sub_his_event)<self._max_his_num:
                    if len(sub_his_event)+len(sub_events)<self._max_his_num:
                        sub_his_event.extend(sub_events)
                        sub_his_event_deltatime.extend([0]*len(sub_events))
                    elif len(sub_his_event)+len(sub_events)==self._max_his_num:
                        sub_his_event.extend(sub_events)
                        sub_his_event_deltatime.extend([0]*len(sub_events))
                        break
                    else:
                        extra = self._max_his_num - len(sub_his_event)
                        selected_index = random.sample(range(len(sub_events)), extra)
                        sub_his_event.extend([sub_events[i] for i in selected_index])
                        sub_his_event_deltatime.extend([0]*extra)
                        break
                sampled_his_event[node_index] = sub_his_event
                his_event_deltatime[node_index] = sub_his_event_deltatime
                isneighbor[node_index] = False
                event_deltatime[node_index] = 0.0
            else:
                sub_his_event = []
                sub_his_event_deltatime = []
                sub_selected_hisevent = []
                sub_selected_hisdeltatime = []
                event_his = node_his_event[type_data[node_index]]
                event_time = event_data[-3]
                for his_index in range(len(event_his)):
                    sub_events = sub_events_list[event_his[his_index]]
                    his_event_time = events_time_list[event_his[his_index]]
                    sub_his_event.extend(sub_events)
                    sub_his_event_deltatime.extend([event_time-his_event_time]*len(sub_events))
                while len(sub_selected_hisevent)<self._max_his_num:
                    extra = self._max_his_num - len(sub_selected_hisevent)
                    if extra>len(sub_his_event):
                        sub_selected_hisevent.extend(sub_his_event)
                        sub_selected_hisdeltatime.extend(sub_his_event_deltatime)
                    else:
                        selected_index = random.sample(range(len(sub_his_event)), extra)
                        sub_selected_hisevent.extend([sub_his_event[i] for i in selected_index])
                        sub_selected_hisdeltatime.extend([sub_his_event_deltatime[i] for i in selected_index])
                sampled_his_event[node_index] = sub_selected_hisevent
                his_event_deltatime[node_index] = sub_selected_hisdeltatime
                isneighbor[node_index] = True
                event_deltatime[node_index] = event_time-events_time_list[event_his[-1]]
        return sampled_his_event, his_event_deltatime, isneighbor, event_deltatime

    # def get_node_his_event_init(self):
    #     node_his_event = [[] for _ in range(self._num_node)]
    #     inited_node = []
    #     sub_events= {**self._sub_events_train, **self._sub_events_valid, **self._sub_events_test}
    #     max_len = 0
    #     max_index = 0
    #     for sub in sub_events:
    #         if len(sub_events[sub]) > max_len:
    #             max_len = len(sub_events[sub])
    #             max_index = sub
    #     print('max_len:%i, index:%i', max_len, max_index)
    #     states = ['train', 'valid', 'test']
    #     for state in states:
    #         #train data
    #         epoch_flag = False
    #         if state == 'train':
    #             data = self.train_data
    #         elif state == 'valid':
    #             data = self.valid_data
    #         elif state == 'test':
    #             data = self.test_data
    #         else:
    #             print('his init state wrong')
    #         data.batch_size = 1
    #         # batches_num = data.get_batch_num()
    #         # print('test')
    #         # print(batches_num)
    #         while not epoch_flag:
    #             batch_data, epoch_flag = data.next_batch()
    #             event_data = batch_data[0]
    #             for node_type in range(self._type_num):
    #                 # print(event_data[node_type])
    #                 for node in event_data[node_type]:
    #                     if node in inited_node:
    #                         continue
    #                     node_his_event[node] = [random.choice(sub_events[event_data[-1]]) for _ in range(self._max_his_num)]
    #                     inited_node.append(node)
    #                     # print(inited_node)
    #                     # time.sleep(1)
    #     return np.asarray(node_his_event, dtype=np.int32)

    def get_batch_feed_dict(self, state, is_init):
    # def get_batch_feed_dict(self, state):
        batch_feed_dict = {}
        batch_feed_dict[self.placeholders['is_init']] = is_init
        if state == 'train':
            batch_data, epoch_flag = self.train_data.next_batch()
            sub_events = self._sub_events_train
            events_time = self._events_time_train
            batch_feed_dict[self.placeholders['keep_prob']] = self._keep
            if self._ns:
                batch_data_neg = self.sample_negbatch_events_withns(batch_data, self._neg_num)
            else:
                batch_data_neg = self.sample_negbatch_events(batch_data, self._neg_num)
        elif state == 'valid':
            batch_data, epoch_flag = self.valid_data.next_batch()
            sub_events = {**self._sub_events_train, **self._sub_events_valid}
            events_time = {**self._events_time_train, **self._events_time_valid}
            batch_feed_dict[self.placeholders['keep_prob']] = 1.0
            batch_data_neg = self.sample_negbatch_events(batch_data, self._neg_num)
        else:
            print('state wrong')
        batch_feed_dict[self.placeholders['nodes_embedding_ph']] = self.node_embedding_cur
        batch_feed_dict[self.placeholders['nodes_cellstates_ph']] = self.node_cellstates_cur
        # batch_feed_dict[self.placeholders['nodes_history_ph']] = self.node_his_event
        # batch_feed_dict[self.placeholders['is_init']] = copy.deepcopy(self.is_init)
        for event in range(self._eventnum_batch):
            event_partition = np.zeros(self._num_node, dtype=np.int32)
            event_data = []
            event_data_type = []
            event_data_neg = [[] for _ in range(self._neg_num)]
            event_data_neg_type = [[] for _ in range(self._neg_num)]
            for node_type in range(self._type_num):
                event_data.extend(batch_data[event][node_type])
                event_data_type.extend([node_type]*len(batch_data[event][node_type]))
                event_partition[batch_data[event][node_type]] = node_type + 1
                # for node in batch_data[event][node_type]:
                #     self.is_init[node] = False
                for neg in range(self._neg_num):
                    event_data_neg[neg].extend(batch_data_neg[event][neg][node_type])
                    event_data_neg_type[neg].extend([node_type]*len(batch_data_neg[event][neg][node_type]))
            # print(batch_data[event])
            # for neg in range(self._neg_num):
            #     print(event_data_neg)
            # time.sleep(10)
            batch_feed_dict[self.placeholders['events_partition_idx_ph'][event]] = event_partition
            batch_feed_dict[self.placeholders['events_nodes_ph'][event]] = np.asarray(event_data, dtype=np.int32)
            batch_feed_dict[self.placeholders['events_nodes_type_ph'][event]] = np.asarray(event_data_type, dtype=np.int32)
            # if len(sub_events[batch_data[event][-1]]) > self._max_his_num:
            #     sample_sub_events = random.sample(sub_events[batch_data[event][-1]], self._max_his_num)
            # else:
            #     sample_sub_events = sub_events[batch_data[event][-1]]
            # batch_feed_dict[self.placeholders['events_sub_ph'][event]] = np.asarray(sample_sub_events, dtype=np.int32)
            sampled_his_event, his_event_deltatime, has_neighbor, event_deltatime = \
                self.sample_subevent_fromhis(batch_data[event], self.node_his_event, sub_events, events_time, self._his_type)
            # batch_feed_dict[self.placeholders['events_deltatime_ph'][event]] = np.asarray(event_deltatime, dtype=np.float64)
            batch_feed_dict[self.placeholders['events_nodes_history_ph'][event]] = np.asarray(sampled_his_event, dtype=np.int32)
            # batch_feed_dict[self.placeholders['events_nodes_history_deltatime_ph'][event]] = np.asarray(his_event_deltatime, dtype=np.float64)
            batch_feed_dict[self.placeholders['has_neighbor'][event]] = has_neighbor
            # batch_feed_dict[self.placeholders['has_neighbor'][event]] = [self.has_neighbor[i] for i in event_data]
            for neg in range(self._neg_num):
                batch_feed_dict[self.placeholders['negevents_nodes_ph'][event][neg]] = \
                        np.asarray(event_data_neg[neg], dtype=np.int32)
                batch_feed_dict[self.placeholders['negevents_nodes_type_ph'][event][neg]] = \
                        np.asarray(event_data_neg_type[neg], dtype=np.int32)
                sampled_his_event_neg, his_event_deltatime_neg, has_neighbor_neg, _ = \
                    self.sample_subevent_fromhis(batch_data_neg[event][neg], self.node_his_event, sub_events, events_time, self._his_type)
                batch_feed_dict[self.placeholders['negevents_nodes_history_ph'][event][neg]] = np.asarray(sampled_his_event_neg, dtype=np.int32)
                # batch_feed_dict[self.placeholders['negevents_nodes_history_deltatime_ph'][event][neg]] = np.asarray(his_event_deltatime_neg, dtype=np.float64)
                batch_feed_dict[self.placeholders['has_neighbor_neg'][event][neg]] = has_neighbor_neg
                # batch_feed_dict[self.placeholders['has_neighbor_neg'][event][neg]] = [self.has_neighbor[i] for i in event_data_neg[neg]]
            for node_type in range(self._type_num):
                for node in batch_data[event][node_type]:
                    self.node_his_event[node].append(batch_data[event][-1])
            # for node in event_data:
            #     self.has_neighbor[node] = True
        return batch_feed_dict, epoch_flag

    def get_feed_dict_eval(self, is_init):
    # def get_feed_dict_eval(self):
        feed_dict_eval = {}
        eval_data, epoch_flag = self.test_data.next_batch()
        sub_events={**self._sub_events_train, **self._sub_events_valid, **self._sub_events_test}
        events_time = {**self._events_time_train, **self._events_time_valid, **self._events_time_test}
        feed_dict_eval[self.placeholders['nodes_embedding_ph']] = self.node_embedding_cur
        feed_dict_eval[self.placeholders['nodes_cellstates_ph']] = self.node_cellstates_cur
        # feed_dict_eval[self.placeholders['nodes_history_ph']] = self.node_his_event
        feed_dict_eval[self.placeholders['is_init']] = is_init
        feed_dict_eval[self.placeholders['keep_prob']] = 1.0
        # feed_dict_eval[self.placeholders['is_init']] = copy.deepcopy(self.is_init)
        eval_data_neg = self.sample_negbatch_events(eval_data, 1)[0][0]
        eval_data = eval_data[0]
        event_partition = np.zeros(self._num_node)
        event_data = []
        event_data_type = []
        event_data_neg = []
        event_data_neg_type = []
        for node_type in range(self._type_num):
            event_data.extend(eval_data[node_type])
            event_data_type.extend([node_type]*len(eval_data[node_type]))
            event_partition[eval_data[node_type]] = node_type+1
            # for node in eval_data[node_type]:
            #     self.is_init[node] = False
            event_data_neg.extend(eval_data_neg[node_type])
            event_data_neg_type.extend([node_type]*len(eval_data_neg[node_type]))
        feed_dict_eval[self.placeholders['event_partition_idx_eval_ph']] = event_partition
        feed_dict_eval[self.placeholders['event_nodes_eval_ph']] = np.asarray(event_data, dtype=np.int32)
        feed_dict_eval[self.placeholders['event_nodes_type_eval_ph']] = np.asarray(event_data_type, dtype=np.int32)
        feed_dict_eval[self.placeholders['negevent_nodes_eval_ph']] = np.asarray(event_data_neg, dtype=np.int32)
        feed_dict_eval[self.placeholders['negevent_nodes_type_eval_ph']] = np.asarray(event_data_neg_type, dtype=np.int32)
        # if len(sub_events[eval_data[-1]]) > self._max_his_num:
        #     sample_sub_events = random.sample(sub_events[eval_data[-1]], self._max_his_num)
        # else:
        #     sample_sub_events = sub_events[eval_data[-1]]
        # feed_dict_eval[self.placeholders['event_sub_eval_ph']] = np.asarray(sample_sub_events, dtype=np.int32)
        sampled_his_event, his_event_deltatime, has_neighbor, event_deltatime = \
            self.sample_subevent_fromhis(eval_data, self.node_his_event, sub_events, events_time, self._his_type)
        sampled_his_event_neg, his_event_deltatime_neg, has_neighbor_neg, _ = \
            self.sample_subevent_fromhis(eval_data_neg, self.node_his_event, sub_events, events_time, self._his_type)
        feed_dict_eval[self.placeholders['event_nodes_history_eval_ph']] = np.asarray(sampled_his_event, dtype=np.int32)
        # feed_dict_eval[self.placeholders['event_nodes_history_deltatime_eval_ph']] = np.asarray(his_event_deltatime, dtype=np.float64)
        # feed_dict_eval[self.placeholders['has_neighbor_eval']] = [self.has_neighbor[i] for i in event_data]
        # feed_dict_eval[self.placeholders['has_neighbor_neg_eval']] = [self.has_neighbor[i] for i in event_data_neg]
        feed_dict_eval[self.placeholders['has_neighbor_eval']] = has_neighbor
        feed_dict_eval[self.placeholders['negevent_nodes_history_eval_ph']] = np.asarray(sampled_his_event_neg, dtype=np.int32)
        # feed_dict_eval[self.placeholders['negevent_nodes_history_deltatime_eval_ph']] = np.asarray(his_event_deltatime_neg, dtype=np.int32)
        feed_dict_eval[self.placeholders['has_neighbor_neg_eval']] = has_neighbor_neg
        # feed_dict_eval[self.placeholders['event_deltatime_eval_ph']] = np.asarray(event_deltatime, dtype=np.float64)
        for node_type in range(self._type_num):
            for node in eval_data[node_type]:
                self.node_his_event[node].append(eval_data[-1])
        # for node in event_data:
        #     self.has_neighbor[node] = True
        return feed_dict_eval, epoch_flag

    def negative_sampling(self, type, neg_num):
        rand_idx = np.random.randint(0, self._neg_table_size, neg_num)
        sampled_node = list(self._neg_table[type][rand_idx])
        return sampled_node

    def _init_neg_table(self):
        for type in range(self._type_num):
            tot_sum, cur_sum, por = 0., 0., 0.
            n_id = 0
            # k_id = list(self.degrees[type].keys())[n_id]
            for k in self.degrees[type].keys():
                tot_sum += np.power(self.degrees[type][k], self._neg_sampling_power)
            for k in range(self._neg_table_size):
                if (k + 1.) / self._neg_table_size > por:
                    k_id = list(self.degrees[type].keys())[n_id]
                    cur_sum += np.power(self.degrees[type][k_id], self._neg_sampling_power)
                    por = cur_sum / tot_sum
                    n_id += 1
                self._neg_table[type][k] = list(self.degrees[type].keys())[n_id-1]
        print('init neg table')

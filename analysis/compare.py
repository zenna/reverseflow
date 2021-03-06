## Compare the different approaches
import pi
from pi import invert
from pi import analysis
import numpy as np
from rf.optim import min_param_error, min_fx_y, gen_y, gen_loss_model, nnet, min_fx_param_error, rightinv_pi_fx
from rf.optim import enhanced_pi, gen_loss_evaluator
from rf.util import *
import rf.templates.res_net
from rf.invert import invert, invert2

import tensorflow as tf
from tensorflow import float32

def search_x(sess, max_time):
    result = min_fx_y(loss_op, batch_loss_op, in_out_var,
                      target_outputs, y_batch, sess, max_time=max_time)
    loss_data, loss_hist, total_time = result


def pointwise_pi(g, gen_graph, inv_inp_gen, check_loss, batch_size, sess,
                 max_time, logdir):
    with g.name_scope('pointwise_pi'):
        in_out_ph = gen_graph(g, batch_size, True)
        print(in_out_ph, "In and Out")
        inv_results = invert(in_out_ph['outputs'])
        inv_g, inv_inputs, inv_outputs_map = inv_results
        inv_outputs_map_canonical = {k: inv_outputs_map[v.name] for k, v in in_out_ph['inputs'].items()}
        result = min_param_error(inv_g, inv_inputs, inv_inp_gen,
                                 inv_outputs_map_canonical,
                                 check_loss, sess, max_time=max_time)
        return result

def min_fx_param(g, gen_graph, inv_inp_gen, fwd_f, batch_size, sess,
                 max_time, logdir):
    with g.name_scope('min_fx_param'):
        in_out_ph = gen_graph(g, batch_size, True)
        inv_results = invert(in_out_ph['outputs'])
        inv_g, inv_inputs, inv_outputs_map = inv_results
        inv_outputs_map_canonical = {k: inv_outputs_map[v.name] for k, v in in_out_ph['inputs'].items()}
        result = min_fx_param_error(inv_g, inv_inputs, inv_inp_gen,
                                 inv_outputs_map_canonical,
                                 fwd_f, sess, max_time=max_time,
                                 optimizer=tf.train.GradientDescentOptimizer(0.0001))
        return result

def nnet_enhanced_pi(g, gen_graph, inv_inp_gen, param_types, param_gen,
                     check_loss, batch_size, sess, max_time, logdir):
    ## Inverse Graph
    with g.name_scope('nnet_enhanced_pi'):
        in_out_ph = gen_graph(g, batch_size, True)
        shrunk_params = {k: tf.placeholder(v['dtype'], shape=v['shape'])
                         for k, v in param_types.items()}
        inv_results = invert(in_out_ph['outputs'], shrunk_params=shrunk_params)
        inv_g, inv_inputs, inv_outputs_map = inv_results

        inv_outputs_map_canonical = {k: inv_outputs_map[v.name]
                                     for k, v in in_out_ph['inputs'].items()}

        writer = tf.train.SummaryWriter(logdir, inv_g)

        # writer = tf.train.SummaryWriter('/home/zenna/repos/inverse/log', inv_g)
        result = enhanced_pi(inv_g, inv_inputs, inv_inp_gen,
                             shrunk_params, param_gen,
                             inv_outputs_map_canonical,
                             check_loss, sess, max_time=max_time)
        return result

def rightinv_pi(g, gen_graph, inv_inp_gen, fwd_f, batch_size, std_loss, sess,
                max_time, seed, logdir):
    ## Inverse Graph
    with g.name_scope('rightinv_pi'):
        in_out_ph = gen_graph(g, batch_size, True, seed=seed)
        inv_results = invert(in_out_ph['outputs'], shrunk_params={})
        inv_g, inv_inputs, inv_outputs_map = inv_results

        inv_outputs_map_canonical = {k: inv_outputs_map[v.name]
                                     for k, v in in_out_ph['inputs'].items()}

        writer = tf.train.SummaryWriter(logdir, inv_g)
        result = rightinv_pi_fx(inv_g, inv_inputs, inv_inp_gen,
                                inv_outputs_map_canonical,
                                fwd_f, sess, seed=seed, max_time=max_time,
                                std_loss=std_loss)
        return result


def loss_checker(g, sess, gen_graph, batch_size):
    in_out_var = gen_graph(g, batch_size, False)
    writer = tf.train.SummaryWriter('/home/zenna/repos/inverse/log', g)
    loss_op, absdiffs, batch_loss_op, batch_loss, target_outputs = gen_loss_model(in_out_var, sess)
    check_loss = gen_loss_evaluator(loss_op, batch_loss, target_outputs, in_out_var["inputs"], sess)
    return check_loss

def compare(gen_graph, fwd_f, param_types, param_gen, options):
    # Preferences
    batch_size = options['batch_size']
    max_time = options['max_time']
    logdir = options['logdir']
    nruns = options['nruns']
    domain_loss_hists = {}
    total_times = {}
    std_loss_hists = {}
    runs = []

    template_kwargs = {'layer_width': 100, 'nblocks': 1, 'block_size': 1, 'output_args' : {'deterministic': True}}

    for i in range(nruns):
        seed = np.random.randint(0, 10000)
        inv_inp_gen = infinite_input(gen_graph, batch_size, seed=seed)
        print("run ", i, "out of ", nruns)
        try:
            if options['pointwise_pi']:
                g_pi = tf.Graph()
                print("Evaluating Pointwise_pi on graph")
                print(summary(g_pi))
                sess_pi = tf.Session(graph=g_pi)
                with g_rf.as_default():
                    check_loss = loss_checker(g_pi, sess_pi, gen_graph, batch_size)
                    result = pointwise_pi(g_pi, gen_graph, inv_inp_gen, check_loss, batch_size,
                                          sess_pi, max_time, logdir)
                    domain_loss_hist, std_loss_hist, total_time = result
                    domain_loss_hists["pointwise_pi"] = domain_loss_hist
                    total_times["pointwise_pi"] = total_time
                    std_loss_hists["pointwise_pi"] = std_loss_hist

            if options['nnet_enhanced_pi']:
                g_npi = tf.Graph()
                sess_npi = tf.Session(graph=g_npi)
                print("nnet enhanced pi")
                print(summary(g_npi))
                with g_nrf.as_default():
                    check_loss = loss_checker(g_npi, sess_npi, gen_graph, batch_size)
                    result = nnet_enhanced_pi(g_npi, gen_graph, inv_inp_gen, param_types, param_gen,
                                              check_loss, batch_size, sess_npi, max_time, logdir)
                    domain_loss_hist, std_loss_hist, total_time = result
                    domain_loss_hists["nnet_enhanced_pi"] = domain_loss_hist
                    total_times["nnet_enhanced_pi"] = total_time
                    std_loss_hists["nnet_enhanced_pi"] = std_loss_hist

            if options['min_fx_y']:
                g_fxy = tf.Graph()
                sess_fxy = tf.Session(graph=g_fxy)
                with g_fxy.as_default():
                    print("BEFORE")
                    detailed_summary(g_fxy)
                    print(summary(g_fxy))
                    print("AFTA")
                    in_out_var = gen_graph(g_fxy, batch_size, False)
                    # assert False
                    print("min fx y pi")
                    # print(summary(g_fxy))
                    writer = tf.train.SummaryWriter('/home/zenna/repos/inverse/log', g_fxy)
                    loss_op, absdiffs, batch_loss_op, batch_loss, target_outputs = gen_loss_model(in_out_var, sess_fxy)
                    # print(summary(g_fxy))
                    check_loss = gen_loss_evaluator(loss_op, batch_loss, target_outputs, in_out_var["inputs"], sess_fxy)
                    result = min_fx_y(loss_op, batch_loss, target_outputs, inv_inp_gen,
                                      sess_fxy, max_iterations=None, max_time=max_time,
                                      time_grain=1.0)
                    std_loss_hist, total_time = result
                    total_times["min_fx_y"] = total_time
                    std_loss_hists["min_fx_y"] = std_loss_hist

            if options['min_fx_param']:
                g_pi_fx = tf.Graph()
                sess_pi_fx = tf.Session(graph=g_pi_fx)
                with g_pi_fx.as_default():
                    print("Evaluating Pointwise_pi on graph")
                    result = min_fx_param(g_pi_fx, gen_graph, inv_inp_gen, fwd_f,
                                          batch_size, sess_pi_fx, max_time, logdir)
                    domain_loss_hist, std_loss_hist, total_time = result
                    domain_loss_hists["min_fx_param"] = domain_loss_hist
                    total_times["min_fx_param"] = total_time
                    std_loss_hists["min_fx_param"] = std_loss_hist

            if options['nnet']:
                g_nnet = tf.Graph()
                sess_nnet = tf.Session(graph=g_nnet)
                template = options['template']
                with g_nnet.as_default():
                    in_out_var = gen_graph(g_nnet, batch_size, False, seed=seed)
                    print("nnet")
                    print(summary(g_nnet))
                    # import pdb; pdb.set_trace()
                    result = nnet(fwd_f, in_out_var['inputs'], in_out_var['outputs'],
                                  inv_inp_gen, template, sess_nnet, max_time=max_time, seed=seed, **template_kwargs)
                    std_loss_hist, total_time = result
                    total_times["nnet"] = total_time
                    std_loss_hists["nnet"] = std_loss_hist

            if options['rightinv_pi_fx']:
                g_rpifx = tf.Graph()
                sess_rpifx = tf.Session(graph=g_rpifx)
                print("right inverse pi")
                print(summary(g_rpifx))
                with g_rpifx.as_default():
                    result = rightinv_pi(g_rpifx, gen_graph, inv_inp_gen,
                                         fwd_f, batch_size, True,
                                         sess_rpifx, max_time, seed, logdir)
                    domain_loss_hist, std_loss_hist, total_time = result
                    domain_loss_hists["rightinv_pi_fx"] = domain_loss_hist
                    total_times["rightinv_pi_fx"] = total_time
                    std_loss_hists["rightinv_pi_fx"] = std_loss_hist

            if options['rightinv_pi_domain']:
                g_rpidom = tf.Graph()
                sess_rpidom = tf.Session(graph=g_rpidom)
                print("right inverse pi: domain")
                print(summary(g_rpidom))
                with g_rpidom.as_default():
                    result = rightinv_pi(g_rpidom, gen_graph, inv_inp_gen,
                                         fwd_f, batch_size, False,
                                         sess_rpidom, max_time, seed, logdir)
                    domain_loss_hist, std_loss_hist, total_time = result
                    domain_loss_hists["rightinv_pi_domain"] = domain_loss_hist
                    total_times["rightinv_pi_domain"] = total_time
                    std_loss_hists["rightinv_pi_domain"] = std_loss_hist

            runs.append({'std_loss_hists': std_loss_hists,
                        'domain_loss_hists': domain_loss_hists,
                        'total_times': total_times})
        except Exception as e:
            raise

    return runs

from bf.compare import compare
import sys
import getopt
import tensorflow as tf
import numpy as np
from bf.util import *
from bf.templates.res_net import res_net_template_dict
from bf.generator import *
import random

for i in range(4):
    g = tf.Graph()
    gen_graph(g, [create_vars, maybe_stop, apply_elem_op])
    writer = tf.train.SummaryWriter('/home/zenna/repos/inverse/log', g)

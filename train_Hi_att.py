import os
import time
import argparse
import random
import numpy as np
import tensorflow as tf
from configs.configs import Configs
from models.baselines_single import build_Hi_att
from utils.read_data import read_essays_single_score_words, read_word_vocab
from utils.general_utils import get_single_scaled_down_score, pad_hierarchical_text_sequences, \
    load_word_embedding_dict, build_embedd_table
from evaluators.multitask_evaluator_single import Evaluator


def main():
    parser = argparse.ArgumentParser(description="PAES_attributes model")
    parser.add_argument('--test_prompt_id', type=int, default=1, help='prompt id of test essay set')
    parser.add_argument('--seed', type=int, default=12, help='set random seed')
    parser.add_argument('--attribute_name', type=str, help='name of the attribute to be trained on')
    args = parser.parse_args()
    test_prompt_id = args.test_prompt_id
    attribute_name = args.attribute_name
    seed = args.seed

    np.random.seed(seed)
    tf.random.set_seed(seed)
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)

    print("Test prompt id is {} of type {}".format(test_prompt_id, type(test_prompt_id)))
    print("Attribute: {}".format(attribute_name))
    print("Seed: {}".format(seed))

    configs = Configs()

    data_path = configs.DATA_PATH
    train_path = data_path + str(test_prompt_id) + '/train.pk'
    dev_path = data_path + str(test_prompt_id) + '/dev.pk'
    test_path = data_path + str(test_prompt_id) + '/test.pk'
    features_path = configs.FEATURES_PATH
    pretrained_embedding = configs.PRETRAINED_EMBEDDING
    embedding_path = configs.EMBEDDING_PATH
    embedding_dim = configs.EMBEDDING_DIM
    readability_path = configs.READABILITY_PATH
    vocab_size = configs.VOCAB_SIZE
    epochs = configs.EPOCHS
    batch_size = configs.BATCH_SIZE

    read_configs = {
        'train_path': train_path,
        'dev_path': dev_path,
        'test_path': test_path,
        'features_path': features_path,
        'readability_path': readability_path,
        'vocab_size': vocab_size
    }

    word_vocab = read_word_vocab(read_configs)
    train_data, dev_data, test_data = read_essays_single_score_words(read_configs, word_vocab, attribute_name)

    if pretrained_embedding:
        embedd_dict, embedd_dim, _ = load_word_embedding_dict(embedding_path)
        embedd_matrix = build_embedd_table(word_vocab, embedd_dict, embedd_dim, caseless=True)
        embed_table = [embedd_matrix]
    else:
        embed_table = None

    max_sentlen = max(train_data['max_sentlen'], dev_data['max_sentlen'], test_data['max_sentlen'])
    max_sentnum = max(train_data['max_sentnum'], dev_data['max_sentnum'], test_data['max_sentnum'])
    print('max sent length: {}'.format(max_sentlen))
    print('max sent num: {}'.format(max_sentnum))
    train_data['y_scaled'] = get_single_scaled_down_score(train_data['data_y'], train_data['prompt_ids'], attribute_name)
    dev_data['y_scaled'] = get_single_scaled_down_score(dev_data['data_y'], dev_data['prompt_ids'], attribute_name)
    test_data['y_scaled'] = get_single_scaled_down_score(test_data['data_y'], test_data['prompt_ids'], attribute_name)

    X_train = pad_hierarchical_text_sequences(train_data['words'], max_sentnum, max_sentlen)
    X_dev = pad_hierarchical_text_sequences(dev_data['words'], max_sentnum, max_sentlen)
    X_test = pad_hierarchical_text_sequences(test_data['words'], max_sentnum, max_sentlen)

    X_train = X_train.reshape((X_train.shape[0], X_train.shape[1] * X_train.shape[2]))
    X_dev = X_dev.reshape((X_dev.shape[0], X_dev.shape[1] * X_dev.shape[2]))
    X_test = X_test.reshape((X_test.shape[0], X_test.shape[1] * X_test.shape[2]))

    X_train_linguistic_features = np.array(train_data['features_x'])
    X_dev_linguistic_features = np.array(dev_data['features_x'])
    X_test_linguistic_features = np.array(test_data['features_x'])

    X_train_readability = np.array(train_data['readability_x'])
    X_dev_readability = np.array(dev_data['readability_x'])
    X_test_readability = np.array(test_data['readability_x'])

    Y_train = np.array(train_data['y_scaled'])
    Y_dev = np.array(dev_data['y_scaled'])
    Y_test = np.array(test_data['y_scaled'])

    print('================================')
    print('X_train_pos: ', X_train.shape)
    print('X_train_readability: ', X_train_readability.shape)
    print('X_train_ling: ', X_train_linguistic_features.shape)
    print('Y_train: ', Y_train.shape)

    print('================================')
    print('X_dev_pos: ', X_dev.shape)
    print('X_dev_readability: ', X_dev_readability.shape)
    print('X_dev_ling: ', X_dev_linguistic_features.shape)
    print('Y_dev: ', Y_dev.shape)

    print('================================')
    print('X_test_pos: ', X_test.shape)
    print('X_test_readability: ', X_test_readability.shape)
    print('X_test_ling: ', X_test_linguistic_features.shape)
    print('Y_test: ', Y_test.shape)
    print('================================')

    model = build_Hi_att(len(word_vocab), max_sentnum, max_sentlen, configs, embed_table)

    dev_features_list = [X_dev]
    test_features_list = [X_test]

    evaluator = Evaluator(test_prompt_id, dev_data['prompt_ids'], test_data['prompt_ids'], dev_features_list,
                          test_features_list, Y_dev, Y_test, attribute_name)

    evaluator.evaluate(model, -1, print_info=True)
    for ii in range(epochs):
        print('Epoch %s/%s' % (str(ii + 1), epochs))
        start_time = time.time()
        model.fit(
            [X_train],
            Y_train, batch_size=batch_size, epochs=1, verbose=0, shuffle=True)
        tt_time = time.time() - start_time
        print("Training one epoch in %.3f s" % tt_time)
        evaluator.evaluate(model, ii + 1)

    evaluator.print_final_info()


if __name__ == '__main__':
    main()

import os
import sys
import re
import numpy as np

from itertools import chain

pattern_num = re.compile(r'[0-9]')
CHAR_PADDING = u"_"
UNKWORD = u"UNKNOWN"
PADDING = u"PADDING"
BOS = u"<BOS>"


def flatten(l):
    return list(chain.from_iterable(l))


def replace_num(text):
    return pattern_num.sub(u'0', text)


def build_vocab(dataset, min_count=0):
    vocab = {}
    vocab[PADDING] = len(vocab)
    vocab[UNKWORD] = len(vocab)
    vocab_cnt = {}
    for d in dataset:
        for w in d:
            vocab_cnt[w] = vocab_cnt.get(w, 0) + 1

    for w, cnt in sorted(vocab_cnt.items(), key=lambda x: x[1], reverse=True):
        if cnt >= min_count:
            vocab[w] = len(vocab)

    return vocab


def build_tag_vocab(dataset, tag_idx=-1):
    pos_tags = list(set(flatten([[w[tag_idx] for w in word_objs]
                                 for word_objs in dataset])))
    pos_tags = sorted(pos_tags)
    vocab = {}
    for pos in pos_tags:
        vocab[pos] = len(vocab)
    return vocab


def write_vocab(filename, vocab):
    f = open(filename, 'w')
    for w, idx in sorted(vocab.items(), key=lambda x: x[1]):
        line = '\t'.join([w.encode('utf-8'), str(idx)])
        f.write(line + '\n')


def load_vocab(filename):
    vocab = {}
    for l in open(filename):
        w, idx = l.decode('utf-8').strip().split(u'\t')
        vocab[w] = int(idx)
    return vocab


def read_raw_file(filename, delimiter=u' '):
    sentences = []
    for l in open(filename):
        words = l.decode('utf-8').strip().split(delimiter)
        words = [(w, -1) for w in words]
        sentences.append(words)
    return sentences


def read_conll_file(filename, delimiter=u'\t', input_idx=0, output_idx=-1):
    sentence = []
    sentences = []
    n_features = -1
    for line_idx, l in enumerate(open(filename, 'r')):
        l_split = l.strip().decode('utf-8').split(delimiter)
        if len(l_split) <= 1:
            if len(sentence) > 0:
                sentences.append(sentence)
                sentence = []
            continue
        else:
            if n_features == -1:
                n_features = len(l_split)

            if n_features != len(l_split):
                val = (str(len(l_split)), str(len(line_idx)))
                err_msg = 'Invalid input feature sizes: "%s". \
                Please check at line [%s]' % val
                raise ValueError(err_msg)
            sentence.append(l_split)
    if len(sentence) > 0:
        sentences.append(sentence)
    return sentences


def load_glove_embedding(filename, vocab):
    word_ids = []
    word_vecs = []
    for i, l in enumerate(open(filename)):
        l = l.decode('utf-8').split(u' ')
        word = l[0].lower()

        if word in vocab:
            word_ids.append(vocab.get(word))
            vec = l[1:]
            vec = map(float, vec)
            word_vecs.append(vec)
    word_ids = np.array(word_ids, dtype=np.int32)
    word_vecs = np.array(word_vecs, dtype=np.float32)
    return word_ids, word_vecs

# Conll 03 shared task evaluation code (IOB format only)


def eval_accuracy(predict_lists):
    sum_cnt = 0
    correct_cnt = 0

    for (gold, pred) in predict_lists:
        sum_cnt += len(gold)
        correct_cnt += sum(gold == pred)

    sum_cnt = 1 if sum_cnt == 0 else sum_cnt
    accuracy = float(correct_cnt) / sum_cnt
    return accuracy


def conll_eval(gold_predict_pairs, flag=True, tag_class=None):
    """
    Args : gold_predict_pairs = [
                                    gold_tags,
                                    predict_tags
                                ]

    """
    if flag:
        gold_tags, predict_tags = zip(*gold_predict_pairs)
    else:
        gold_tags, predict_tags = gold_predict_pairs

    n_phrase_gold = 0
    n_phrases_tag_gold = 0
    n_phrases_dict = {}
    n_phrases_dict['gold'] = {}
    n_phrases_dict['predict'] = {}
    cnt_phrases_dict = {}
    evals = {}

    for tag_name in tag_class:
        cnt_phrases_dict[tag_name] = {}
        cnt_phrases_dict[tag_name]['predict_cnt'] = 0
        cnt_phrases_dict[tag_name]['gold_cnt'] = 0
        cnt_phrases_dict[tag_name]['correct_cnt'] = 0

    for i in xrange(len(gold_tags)):
        gold = gold_tags[i]
        predict = predict_tags[i]

        gold_phrases = IOB_to_range_format_one(gold, is_test_mode=True)
        predict_phrases = IOB_to_range_format_one(predict, is_test_mode=True)
        for p in gold_phrases:
            tag_name = p[-1]
            n_phrases_dict['gold'][tag_name] = n_phrases_dict['gold'].get(tag_name, 0) + 1

        for p in predict_phrases:
            tag_name = p[-1]
            n_phrases_dict['predict'][tag_name] = n_phrases_dict['predict'].get(tag_name, 0) + 1

        for tag_name in tag_class:
            _gold_phrases = [_ for _ in gold_phrases if _[-1] == tag_name]
            _predict_phrases = [_ for _ in predict_phrases if _[-1] == tag_name]

            correct_cnt, gold_cnt, predict_cnt = range_metric_cnt(_gold_phrases, _predict_phrases)
            cnt_phrases_dict[tag_name]['gold_cnt'] += gold_cnt if len(_gold_phrases) > 0 else 0
            cnt_phrases_dict[tag_name][
                'predict_cnt'] += predict_cnt if len(_predict_phrases) > 0 else 0
            cnt_phrases_dict[tag_name]['correct_cnt'] += correct_cnt

    lst_gold_phrase = n_phrases_dict['gold']
    lst_predict_phrase = n_phrases_dict['predict']
    num_gold_phrase = sum(n_phrases_dict['gold'].values())
    num_predict_phrase = sum(n_phrases_dict['predict'].values())
    phrase_info = [num_gold_phrase, num_predict_phrase, lst_gold_phrase, lst_predict_phrase]

    for tag_name in tag_class:
        recall = cnt_phrases_dict[tag_name][
            'correct_cnt'] / float(cnt_phrases_dict[tag_name]['gold_cnt']) if cnt_phrases_dict[tag_name]['gold_cnt'] else 0.0
        precision = cnt_phrases_dict[tag_name]['correct_cnt'] / float(
            cnt_phrases_dict[tag_name]['predict_cnt']) if cnt_phrases_dict[tag_name]['predict_cnt'] else 0.0
        sum_recall_precision = 1.0 if recall + precision == 0.0 else recall + precision
        f_measure = (2 * recall * precision) / (sum_recall_precision)
        evals[tag_name] = [precision * 100.0, recall * 100.0, f_measure * 100.0]

    correct_cnt = sum([ev['correct_cnt'] for tag_name, ev in cnt_phrases_dict.items()])
    gold_cnt = sum([ev['gold_cnt'] for tag_name, ev in cnt_phrases_dict.items()])
    predict_cnt = sum([ev['predict_cnt'] for tag_name, ev in cnt_phrases_dict.items()])

    recall = correct_cnt / float(gold_cnt) if gold_cnt else 0.0
    precision = correct_cnt / float(predict_cnt) if predict_cnt else 0.0
    sum_recall_precision = 1.0 if recall + precision == 0.0 else recall + precision
    f_measure = (2 * recall * precision) / (sum_recall_precision)
    evals['All_Result'] = [precision * 100.0, recall * 100.0, f_measure * 100.0]
    return evals, phrase_info


def IOB_to_range_format_one(tag_list, is_test_mode=False):
    sentence_lst = []
    ner = []
    ner_type = []
    # print tag_list
    for i in xrange(len(tag_list)):
        prev_tag = tag_list[i - 1] if i != 0 else ''
        prev_tag_type = prev_tag[2:]
        # prev_tag_head = tag_list[i-1][0] if i != 0 else ''
        tag = tag_list[i]
        tag_type = tag[2:]
        tag_head = tag_list[i][0]
        ner_is_exist = len(ner) > 0
        ner_is_end = (ner_is_exist and tag_head == u'O') or (ner_is_exist and tag_head == u'B') or (
            ner_is_exist and tag_head == u'I' and prev_tag_type != tag_type)
        # NOTE: In Conll 2003 evaluation code, I-ORG means NE start!!
        # ner_is_end_conll = (tag_head == u'I' and prev_tag_type != tag_type and not ner_is_exist)
        if ner_is_end:
            if is_test_mode and len(set(ner_type)) != 1:
                ner_type = [list(set(ner_type))[0]]
            assert len(set(ner_type)) == 1
            ner_type = ner_type[0]
            ner = (ner[0], ner[-1], ner_type) if len(ner) > 1 else (ner[0], ner[0], ner_type)
            sentence_lst.append(ner)
            ner = [i] if tag_head == u'B' or tag_head == u'I' else []
            ner_type = [tag_type] if tag_head == u'B' or tag_head == u'I' else []
        elif tag_head == u'B' or (tag_head == u'I' and (tag_type != prev_tag_type)):
            ner = [i]
            ner_type = [tag_type]
        elif tag_head == u'I' and prev_tag_type == tag_type and ner_is_exist:
            ner.append(i)
            ner_type.append(tag_type)

    if len(ner) > 0:
        ner_type = ner_type[0]
        ner = (ner[0], ner[-1], ner_type) if len(ner) > 1 else (ner[0], ner[0], ner_type)
        sentence_lst.append(ner)
    return sentence_lst


def range_metric_cnt(gold_range_list, predict_range_list):
    gold_range_set = set(gold_range_list)
    predict_range_set = set(predict_range_list)
    TP = gold_range_set & predict_range_set
    _g = len(gold_range_set)
    _p = len(predict_range_set)
    correct_cnt = len(TP)
    gold_cnt = _g
    predict_cnt = _p
    return correct_cnt, gold_cnt, predict_cnt


def parse_to_word_ids(sentences, xp, vocab, UNK_IDX, idx=0):
    x_data = [xp.array([vocab.get(w[idx].lower(), UNK_IDX)
                        for w in sentence], dtype=xp.int32)
              for sentence in sentences]
    return x_data


def parse_to_char_ids(sentences, xp, vocab_char, UNK_IDX, idx=0):
    x_data = [[xp.array([vocab_char.get(c, UNK_IDX) for c in w[idx]],
                        dtype=xp.int32)
               for w in sentence]
              for sentence in sentences]
    return x_data


def parse_to_tag_ids(sentences, xp, vocab, UNK_IDX, idx=-1):
    x_data = [xp.array([vocab.get(w[idx], UNK_IDX)
                        for w in sentence], dtype=xp.int32)
              for sentence in sentences]
    return x_data

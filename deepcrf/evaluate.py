
import util
import util_talbes


def load_file(filename):
    alltags_list = []
    tags = []
    for l in open(filename):
        tag = l.decode('utf-8').strip()
        if tag == u'':
            # sentence split
            alltags_list.append(tags)
            tags = []
        else:
            tags.append(tag)
    if len(tags):
        alltags_list.append(tags)
        tags = []
    return alltags_list


def uniq_tagset(alltags_list, tag_names=[]):
    for tags in alltags_list:
        for tag in tags:
            tagname = '-'.join(tag.split(u'-')[1:])
            if tagname != u'' and tagname not in tag_names:
                tag_names.append(tagname)
    return tag_names


def run(gold_file, predicted_file, **args):
    gold_tags = load_file(gold_file)
    predicted_tags = load_file(predicted_file)

    # tag set
    tag_names = []
    tag_names = uniq_tagset(gold_tags, tag_names)
    tag_names = uniq_tagset(predicted_tags, tag_names)
    gold_predict_pairs = [gold_tags, predicted_tags]
    result, phrase_info = util.conll_eval(gold_predict_pairs, flag=False, tag_class=tag_names)

    table = util_talbes.SimpleTable()
    table.set_header(('Tag Name', 'Precision', 'Recall', 'F_measure'))

    all_result = result['All_Result']
    table.add_row(['All_Result'] + all_result)

    for key in result.keys():
        if key != 'All_Result':
            r = result[key]
            table.add_row([key] + r)

    table.print_table()

    # accuracy = util.eval_accuracy(gold_predict_pairs, flag=False)
    # print 'Tag Accuracy:', accuracy

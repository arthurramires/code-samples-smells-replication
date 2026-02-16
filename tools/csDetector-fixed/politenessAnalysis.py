import os
import csv
import convokit

import statsAnalysis as stats
from configuration import Configuration


def politenessAnalysis(
    config: Configuration,
    prCommentBatches: list,
    issueCommentBatches: list,
):
    calculateACCL(config, prCommentBatches, issueCommentBatches)

    

    calculateRPC(config, "PR", prCommentBatches)
    # FIX: original code passed prCommentBatches for both PR and Issue
    calculateRPC(config, "Issue", issueCommentBatches)


def calculateACCL(config, prCommentBatches, issueCommentBatches):
    for batchIdx, batch in enumerate(prCommentBatches):

        try:
            prCommentLengths = list([len(c) for c in batch])
            issueCommentBatch = list([len(c) for c in issueCommentBatches[batchIdx]])

            prCommentLengthsMean = stats.calculateStats(prCommentLengths)["mean"]
            issueCommentLengthsMean = stats.calculateStats(issueCommentBatch)["mean"]

            # FIX: original had operator precedence bug: a + b / 2 != (a + b) / 2
            accl = (prCommentLengthsMean + issueCommentLengthsMean) / 2
        except Exception as e:
            print(f"  WARNING: ACCL analysis failed for batch {batchIdx}: {e}")
            accl = 0

        # output results
        with open(os.path.join(config.resultsPath, f"results_{batchIdx}.csv"),
                  "a",
                  newline=""
                  ) as f:
            w = csv.writer(f, delimiter=",")
            w.writerow([f"ACCL", accl])


def calculateRPC(config, outputPrefix, commentBatches):
    for batchIdx, batch in enumerate(commentBatches):

        # analyze batch
        try:
            positiveMarkerCount = getResults(batch)
        except Exception as e:
            print(f"  WARNING: RPC analysis failed for {outputPrefix} batch {batchIdx}: {e}")
            positiveMarkerCount = 0

        # output results
        with open(
            os.path.join(config.resultsPath, f"results_{batchIdx}.csv"),
            "a",
            newline="",
        ) as f:
            w = csv.writer(f, delimiter=",")
            w.writerow([f"RPC{outputPrefix}", positiveMarkerCount])


def getResults(comments: list):

    # FIX: handle empty comment list
    if len(comments) == 0:
        return 0

    # define default speaker
    speaker = convokit.Speaker(id="default", name="default")

    # build utterance list
    utterances = list(
        [
            convokit.Utterance(id=str(idx), speaker=speaker, text=comment)
            for idx, comment in enumerate(comments)
        ]
    )

    # build corpus
    corpus = convokit.Corpus(utterances=utterances)

    # parse
    parser = convokit.TextParser(verbosity=1000)
    corpus = parser.transform(corpus)

    # extract politeness features
    politeness = convokit.PolitenessStrategies()
    corpus = politeness.transform(corpus, markers=True)
    features = corpus.get_utterances_dataframe()

    # get positive politeness marker count
    positiveMarkerCount = sum(
        [
            feature["feature_politeness_==HASPOSITIVE=="]
            for feature in features["meta.politeness_strategies"]
        ]
    )

    return positiveMarkerCount

from statistics import *
import os
import csv


def outputStatistics(idx: int, data: list, metric: str, outputDir: str):

    # validate
    if len(data) < 1:
        return

    # calculate and output
    stats = calculateStats(data)

    # output
    with open(os.path.join(outputDir, f"results_{idx}.csv"), "a", newline="") as f:
        w = csv.writer(f, delimiter=",")

        for key in stats:
            outputValue(w, metric, key, stats)


def calculateStats(data):

    # FIX: handle empty data list
    if len(data) == 0:
        return dict(count=0, mean=0, stdev=0)

    stats = dict(
        count=len(data),
        mean=mean(data),
        stdev=stdev(data) if len(data) > 1 else 0
    )

    return stats


def outputValue(w, metric: str, name: str, dict: dict):
    value = dict[name]
    name = "{0}_{1}".format(metric, name)
    w.writerow([name, value])

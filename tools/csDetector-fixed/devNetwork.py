import sys
import os
import subprocess
import shutil
import stat
import git
import pkg_resources
import sentistrength

from configuration import parseDevNetworkArgs
from repoLoader import getRepo
from aliasWorker import replaceAliases
from commitAnalysis import commitAnalysis
import centralityAnalysis as centrality
from tagAnalysis import tagAnalysis
from devAnalysis import devAnalysis
from graphqlAnalysis.releaseAnalysis import releaseAnalysis
from graphqlAnalysis.prAnalysis import prAnalysis
from graphqlAnalysis.issueAnalysis import issueAnalysis
from smellDetection import smellDetection
from politenessAnalysis import politenessAnalysis
from dateutil.relativedelta import relativedelta

# FIX: original code crashed on Mac/Linux because WINDIR env var doesn't exist
FILEBROWSER_PATH = None
if os.name == 'nt':
    FILEBROWSER_PATH = os.path.join(os.getenv("WINDIR", ""), "explorer.exe")


def main(argv):
    try:
        # validate running in venv
        if not hasattr(sys, "prefix"):
            raise Exception(
                "The tool does not appear to be running in the virtual environment!\nSee README for activation."
            )

        # FIX: relaxed Python version check (original required exactly 3.8)
        if sys.version_info.major != 3 or sys.version_info.minor < 8:
            raise Exception(
                "Expected Python 3.8+ as runtime but got {0}.{1}, the tool might not run as expected!\nSee README for stack requirements.".format(
                    sys.version_info.major,
                    sys.version_info.minor,
                )
            )
        if sys.version_info.minor != 8:
            print(f"WARNING: Running on Python 3.{sys.version_info.minor} (originally designed for 3.8). Proceeding anyway.")

        # validate installed modules
        # FIX: pkg_resources.working_set can fail on Python 3.10+; wrap in try/except
        try:
            required = {
                "wheel",
                "networkx",
                "pandas",
                "matplotlib",
                "gitpython",
                "requests",
                "pyyaml",
                "progress",
                "strsimpy",
                "python-dateutil",
                "sentistrength",
                "joblib",
            }
            installed = {pkg for pkg in pkg_resources.working_set.by_key}
            missing = required - installed

            if len(missing) > 0:
                print(f"WARNING: Possibly missing modules: {missing} (continuing anyway)")
        except Exception as e:
            print(f"WARNING: Could not validate modules ({e}), continuing anyway")

        # parse args
        config = parseDevNetworkArgs(sys.argv)
        # prepare folders
        if os.path.exists(config.resultsPath):
            remove_tree(config.resultsPath)

        os.makedirs(config.metricsPath)

        # get repository reference
        repo = getRepo(config)

        # setup sentiment analysis
        senti = sentistrength.PySentiStr()

        sentiJarPath = os.path.join(config.sentiStrengthPath, "SentiStrength.jar").replace("\\", "/")
        senti.setSentiStrengthPath(sentiJarPath)

        sentiDataPath = os.path.join(config.sentiStrengthPath, "SentiStrength_Data").replace("\\", "/") + "/"
        senti.setSentiStrengthLanguageFolderPath(sentiDataPath)

        # prepare batch delta
        delta = relativedelta(months=+config.batchMonths)

        # handle aliases
        commits = list(replaceAliases(repo.iter_commits(), config))

        # run analysis
        batchDates, authorInfoDict, daysActive = commitAnalysis(
            senti, commits, delta, config
        )

        try:
            tagAnalysis(repo, delta, batchDates, daysActive, config)
        except Exception as e:
            print(f"WARNING: Tag analysis failed: {e}")

        coreDevs = centrality.centralityAnalysis(commits, delta, batchDates, config)

        try:
            releaseAnalysis(commits, config, delta, batchDates)
        except Exception as e:
            print(f"WARNING: Release analysis failed: {e}")

        # FIX: wrap PR/Issue/Politeness in try/except so commit+centrality data is still saved
        prParticipantBatches = [[] for _ in batchDates]
        prCommentBatches = [[] for _ in batchDates]
        issueParticipantBatches = [[] for _ in batchDates]
        issueCommentBatches = [[] for _ in batchDates]

        try:
            prParticipantBatches, prCommentBatches = prAnalysis(
                config,
                senti,
                delta,
                batchDates,
            )
            # FIX: pad to match batchDates length (repos with few PRs return shorter lists)
            while len(prParticipantBatches) < len(batchDates):
                prParticipantBatches.append([])
            while len(prCommentBatches) < len(batchDates):
                prCommentBatches.append([])
        except Exception as e:
            print(f"WARNING: PR analysis failed: {e}")

        try:
            issueParticipantBatches, issueCommentBatches = issueAnalysis(
                config,
                senti,
                delta,
                batchDates,
            )
            # FIX: pad to match batchDates length (repos with few issues return shorter lists)
            while len(issueParticipantBatches) < len(batchDates):
                issueParticipantBatches.append([])
            while len(issueCommentBatches) < len(batchDates):
                issueCommentBatches.append([])
        except Exception as e:
            print(f"WARNING: Issue analysis failed: {e}")

        try:
            politenessAnalysis(config, prCommentBatches, issueCommentBatches)
        except Exception as e:
            print(f"WARNING: Politeness analysis failed: {e}")

        for batchIdx, batchDate in enumerate(batchDates):

            # get combined author lists
            combinedAuthorsInBatch = (
                prParticipantBatches[batchIdx] + issueParticipantBatches[batchIdx]
            )

            # build combined network
            centrality.buildGraphQlNetwork(
                batchIdx,
                combinedAuthorsInBatch,
                "issuesAndPRsCentrality",
                config,
            )

            # get combined unique authors for both PRs and issues
            uniqueAuthorsInPrBatch = set(
                author for pr in prParticipantBatches[batchIdx] for author in pr
            )

            uniqueAuthorsInIssueBatch = set(
                author for pr in issueParticipantBatches[batchIdx] for author in pr
            )

            uniqueAuthorsInBatch = uniqueAuthorsInPrBatch.union(
                uniqueAuthorsInIssueBatch
            )

            # get batch core team
            batchCoreDevs = coreDevs[batchIdx]

            # run dev analysis
            try:
                devAnalysis(
                    authorInfoDict,
                    batchIdx,
                    uniqueAuthorsInBatch,
                    batchCoreDevs,
                    config,
                )
            except Exception as e:
                print(f"WARNING: Dev analysis failed for batch {batchIdx}: {e}")

            # run smell detection
            try:
                smellDetection(config, batchIdx)
            except Exception as e:
                print(f"WARNING: Smell detection failed for batch {batchIdx}: {e}")
                print("  (metrics were still saved — smell detection requires matching scikit-learn version)")

    finally:
        # close repo to avoid resource leaks
        if "repo" in locals():
            del repo


class Progress(git.remote.RemoteProgress):
    def update(self, op_code, cur_count, max_count=None, message=""):
        print(self._cur_line, end="\r")


def commitDate(tag):
    return tag.commit.committed_date


def remove_readonly(fn, path, excinfo):
    os.chmod(path, stat.S_IWRITE)
    remove_tree(path)


def remove_tree(path):
    if os.path.isdir(path):
        shutil.rmtree(path, onerror=remove_readonly)
    else:
        os.remove(path)


# https://stackoverflow.com/a/50965628
def explore(path):
    # explorer would choke on forward slashes
    path = os.path.normpath(path)

    if os.path.isdir(path):
        subprocess.run([FILEBROWSER_PATH, path])
    elif os.path.isfile(path):
        subprocess.run([FILEBROWSER_PATH, "/select,", os.path.normpath(path)])


if __name__ == "__main__":
    main(sys.argv[1:])

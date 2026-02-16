import os
import git
import shutil

from configuration import Configuration


def getRepo(config: Configuration):

    # build path
    repoPath = os.path.join(
        config.repositoryPath,
        "{}.{}".format(config.repositoryOwner, config.repositoryName),
    )

    # get repository reference
    repo = None
    if not os.path.exists(repoPath):
        print("Downloading repository...")
        # FIX: try "master" first, then "main", then default branch
        for branch_name in ["master", "main", None]:
            try:
                clone_kwargs = dict(
                    progress=Progress(),
                    odbt=git.GitCmdObjectDB,
                )
                if branch_name is not None:
                    clone_kwargs["branch"] = branch_name
                repo = git.Repo.clone_from(
                    config.repositoryUrl,
                    repoPath,
                    **clone_kwargs,
                )
                print(f"\nCloned successfully (branch: {branch_name or 'default'})")
                break
            except git.exc.GitCommandError as e:
                if branch_name is not None:
                    print(f"\nBranch '{branch_name}' not found, trying next...")
                    if os.path.exists(repoPath):
                        shutil.rmtree(repoPath, ignore_errors=True)
                else:
                    raise e
        print()
    else:
        # FIX: validate existing directory is actually a git repo
        try:
            repo = git.Repo(repoPath, odbt=git.GitCmdObjectDB)
        except (git.exc.InvalidGitRepositoryError, git.exc.NoSuchPathError):
            print(f"Invalid repo at {repoPath}, re-cloning...")
            shutil.rmtree(repoPath, ignore_errors=True)
            return getRepo(config)  # retry clone

    return repo


class Progress(git.remote.RemoteProgress):
    def update(self, op_code, cur_count, max_count=None, message=""):
        print(self._cur_line, end="\r")
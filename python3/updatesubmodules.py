import os
import logging
from gitclient import GitClient

FAILURE = 1
SUCCESS = 0

logger = logging.getLogger('gitclient')

                # git checkout master
                # git pull
                # git submodule update --init --recursive



def updateCSharedUtility(git):
	status = git.status()
	if status == None:
		logger.error("[c-shared] failed getting status")
		result = FAILURE
	elif len(status.staged) != 0 or len(status.staged) != 0 or len(status.staged) != 0:
		logger.error("[c-shared] repo is not clean. Revert all changes before proceeding")
		result = FAILURE
	elif git.checkout('master') != 0:
		logger.error("[c-shared] failed checking out master")
		result = FAILURE
	elif git.pull() != 0:
	

git = GitClient.open()
current_step = Step.OpenRepo

if git == None:
	result = FAILURE
else:
	updateCSharedUtility(git) != 0:
	
	
	
return result
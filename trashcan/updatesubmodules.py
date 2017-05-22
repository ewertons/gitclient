import sys
import os
import logging
# import jenkins
from gitclient import GitClient

FAILURE = 1
SUCCESS = 0
AZURE_IOT_SDK_C_REPO_URL = "https://github.com/Azure/azure-iot-sdk-c.git"

logger = logging.getLogger('submupd')
logger.setLevel(logging.DEBUG)
logger_handler_console = logging.StreamHandler()
logger_handler_console.setLevel(logging.DEBUG)
logger_formatter = logging.Formatter('%(asctime)s [%(name)s] [%(levelname)s] %(message)s')
logger_handler_console.setFormatter(logger_formatter)
logger.addHandler(logger_handler_console)

class ParsedArgs:
	username = None
	password = None
	
	@staticmethod
	def parse(argv):
		if len(argv) != 3:
			logger.error("invalid arguments. Expected: <username> <password>")
			result = None
		else:
			result = ParsedArgs()
			result.username = argv[1]
			result.password = argv[2]
	
		return result

def runJobIntegrateIntoRepoC(credentials=None, commit_id='', url='', branch='master'):
	build_id = None
	return build_id;
	
def waitForJobCompletion(credentials=None, build_id=None, maxWaitTimeSecs=1800):
	result = True
	
	
	
	return result
	
def openAndVerifyRepo():
	logger.info("opening and verifying azure-iot-sdk-c local repo")
	
	git = GitClient.open()
	
	if git != None:
		remote_info = git.remote()
		
		if remote_info == None:
			logger.error("failed opening and verifying repo (failed getting remote info)")
			git = None
		elif remote_info[0].url != AZURE_IOT_SDK_C_REPO_URL:
			logger.error("failed opening and verifying repo (not at expected azure-iot-sdk-c repo)")
			git = None
	
	return git

def updateCSharedUtility(git):
	logger.info("updating submodule azure-iot-c-shared-utility")
	
	status = git.status()
	if status == None:
		logger.error("[c-shared] failed getting status")
	elif len(status.staged) != 0 or len(status.staged) != 0 or len(status.staged) != 0:
		logger.error("[c-shared] repo is not clean. Revert all changes before proceeding")
	elif git.checkout('master') != 0:
		logger.error("[c-shared] failed checking out master")
	elif git.pull() != 0:
		logger.error("[c-shared] failed pulling origin")
	
	return None
		
def updateUAMQP(git):
	return False
	
def updateUMQTT(git):
	return False

def updateAzureIoTSdkC(git):
	return False
	
def mergeUpdatesToMaster(git):
	return False

parsed_args = ParsedArgs.parse(sys.argv)

if parsed_args == None:	
	result = FAILURE
else:
	git = openAndVerifyRepo()

	if git == None:
		result = FAILURE
	else:
		cshared_commit = updateCSharedUtility(git)
		
		if cshared_commit == None:
			result = FAILURE
		elif not updateUAMQP(git, cshared_commit):
			result = FAILURE
		elif not updateUMQTT(git, cshared_commit):
			result = FAILURE
		elif not updateAzureIoTSdkC(git):
			result = FAILURE
		elif not mergeUpdatesToMaster(git)
			result = FAILURE
		else:
			result = SUCCESS
	
sys.exit(result)
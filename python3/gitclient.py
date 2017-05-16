import subprocess
import re
import os
import logging

logger = logging.getLogger('gitclient')
logger.setLevel(logging.DEBUG)
logger_handler_console = logging.StreamHandler()
logger_handler_console.setLevel(logging.DEBUG)
logger_formatter = logging.Formatter('%(asctime)s [%(name)s] [%(levelname)s] %(message)s')
logger_handler_console.setFormatter(logger_formatter)
logger.addHandler(logger_handler_console)

class command:
	output = ''
	returncode = 0

	def __str__(self):
		return 'returncode=%d\r\noutput=%s' %(self.returncode, self.output)
	
	@staticmethod
	def execute(cmd):
		result = command()
		try:
			result.output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
			result.returncode = 0
		except subprocess.CalledProcessError as e:
			result.output = e.output
			result.returncode = e.returncode 

		return result

class GitFileChangeDescription:
	change_type = None
	file = ''
	
	def __str__(self):
		if self.change_type != None:
			string = '%s (%s)' %(self.file.decode(), self.change_type.decode())
		else:
			string = '%s' %(self.file.decode())
			
		return string
	
	@staticmethod
	def parse(line):
		result = GitFileChangeDescription()
		line = line.replace(b'(new commits)', b'')
		line = line.strip()

		tokens = line.split(b':')
		
		if len(tokens) == 1:
			result.file = tokens[0]
		else:
			result.change_type = tokens[0]
			result.file = tokens[1].strip()

		return result

class GitStatus:
	branch = ''
	staged = []
	not_staged = []
	untracked = []
	
	def __str__(self):
		string = 'branch: %s' %(self.branch)
		
		if len(self.staged) > 0:
			string = string + '\r\nStaged:'
			for file in self.staged:
				string = string + '\r\n\t' + str(file)
		if len(self.not_staged) > 0:
			string = string + '\r\nNot staged:'
			for file in self.not_staged:
				string = string + '\r\n\t' + str(file)
		if len(self.untracked) > 0:
			string = string + '\r\nUntracked:'
			for file in self.untracked:
				string = string + '\r\n\t' + str(file)

		return string
	
	@staticmethod
	def parse(cmdres):
		result = None
		
		if cmdres != None:
			result = GitStatus()
			is_reading_staged = False
			is_reading_not_staged = False
			is_reading_untracked = False

			for line in cmdres.output.split(b'\n'):
				if b'(use' in line or line == b'':
					continue
				elif b'Changes to be committed' in line:
					is_reading_staged = True
					is_reading_not_staged = False
					is_reading_untracked = False
				elif b'Changes not staged for commit' in line:
					is_reading_staged = False
					is_reading_not_staged = True
					is_reading_untracked = False
				elif b'Untracked files' in line:
					is_reading_staged = False
					is_reading_not_staged = False
					is_reading_untracked = True
				elif is_reading_staged == True:
					file = GitFileChangeDescription.parse(line)
					if file != None:
						result.staged.append(file)
				elif is_reading_not_staged == True:
					file = GitFileChangeDescription.parse(line)
					if file != None:
						result.not_staged.append(file)
				elif is_reading_untracked == True:
					file = GitFileChangeDescription.parse(line)
					if file != None:
						result.untracked.append(file)
				elif b'On branch' in line:
					result.branch = line.split(b' ')[2]
			
		return result

class GitSubmoduleStatus:
	is_current_commit_checked_out = True
	is_initialized = True
	has_merge_conflicts = False
	current_commit_id_checked_out = None
	path = None
	
	def __str__(self):
		attributes = []
		
		if not self.is_current_commit_checked_out:
			attributes.append('+')
		if self.has_merge_conflicts:
			attributes.append('U')
		if not self.is_initialized:
			attributes.append('-')
		
		if len(attributes) > 0:
			attributes = ",".join(attributes)
			attributes = '(' + attributes + ')'
			string = '%s %s %s' %(self.current_commit_id_checked_out.decode(), self.path.decode(), attributes)
		else:
			string = '%s %s' %(self.current_commit_id_checked_out.decode(), self.path.decode())
	
		return string
		
	@staticmethod
	def parse(cmdres):
		result = None
		
		if cmdres.returncode == 0:
			result = []
			for line in cmdres.output.split(b'\n'):
				if line == b'':
					continue
					
				item = GitSubmoduleStatus()
				
				if line[0:1] == b'U':
					item.has_merge_conflicts = True
				elif line[0:1] == b'-':
					item.is_initialized = False
				elif line[0:1] == b'+':
					item.is_current_commit_checked_out = False
		
				item.current_commit_id_checked_out = line[1:41]
				item.path = line[42:line.index(b' (')]
				result.append(item)
		
		return result
		
		
class GitClient:
	@staticmethod
	def clone(path='.', url='', recursive=False):
		result = None
		
		if url == '':
			logger.error("cannot clone repo (invalid url)")
			result = None
		else:
			try:
				os.chdir(path)
				full_cmd = "git clone %s" % (url)
				logger.info(full_cmd)
				output = subprocess.check_output(full_cmd)
			except:
				result = None
		
		
		return result
		
	@staticmethod
	def open(path='.'):
		result = None
		
		try:
			logger.info('Opening git repo %s' %(path))
			
			if path != '.':
				os.chdir(path)
				
			cmd = command.execute("git status")
			
			if cmd.output.find(b'Not a git repository') != -1:
				logger.error('Not a git repository')
				result = None
			else:
				result = GitClient() 
		except:
			logger.error("Failed opening repository")
			result = None
		
		return result

	def status(self):
		result = None;
		
		full_cmd = "git status"
		
		logger.info(full_cmd)
		
		cmd = command.execute(full_cmd)
		
		if cmd.returncode != 0:
			logger.error("git status returned %s, code=%d", cmd.output, cmd.returncode)
			result = None
		else:
			result = GitStatus.parse(cmd)
		
		return result
		
	def submodule(self, subcmd = 'status', recursive=False, init=False, deinit=False):
		result = None;
		
		full_cmd = "git submodule %s" %(subcmd)
		
		if recursive:
			full_cmd = full_cmd + " --recursive"
		if init:
			full_cmd = full_cmd + " --init"
		if deinit:
			full_cmd = full_cmd + " --deinit"
	
		logger.info(full_cmd)
		
		cmd = command.execute(full_cmd)
		
		if cmd.returncode != 0:
			logger.error("git %s returned %s, code=%d", subcmd, cmd.output, cmd.returncode)
			result = None
		else:
			if subcmd == 'status':
				result = GitSubmoduleStatus.parse(cmd)
			else:
				result = cmd.returncode

		return result

	def checkout(self, target='')
		result = None
		
		if target == b'':
			logger.error("Cannot checkout, target not provided")
		else:
			full_cmd = "git checkout %s" %(target)
			cmd = command.execute(full_cmd)
			
			if cmd.returncode != 0:
				logger.error("git checkout returned %s, code=%d", cmd.output, cmd.returncode)
			else:
				result = cmd.returncode
				
		return result

git = GitClient.open()

if git != None:
	status = git.status()
	print((status))
	git.submodule(subcmd='update')
	
	for item in git.submodule():
		print(item)
	
	git.checkout("iothub_client//tests//longhaul_tests//main.c")
	
	status = git.status()
		print((status))
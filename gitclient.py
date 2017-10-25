import subprocess
import re
import os
import logging

#TODO:
# add API to set credentials (Ammon Larsen)

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

class GitRemote:
	name = None
	url = None
	type = None
	
	@staticmethod
	def parse(cmdres):
		result = []
		
		lines = cmdres.output.split(b'\n')
		
		for line in lines:
			if line == b'':
				continue;
		
			tokens = []
			for token in line.split(b' '):
				sub_tokens = token.split(b'\t')
				
				if len(sub_tokens) > 0:
					for sub_token in sub_tokens:
						tokens.append(sub_token)
				else:
					tokens.append(token)
			
			item = GitRemote()
			item.name = tokens[0]
			item.url = tokens[1]
			item.type = tokens[2]
			
			result.append(item)
		
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

class GitLog:
	commit = None
	author = None
	date = None
	description = None
	merge = None

	def __str__(self):
		string = 'commit %s\r\nAuthor: %s\r\nDate: %s' %(self.commit.decode(), self.author.decode(), self.date.decode())
		return string

	@staticmethod
	def parse(cmdres):
		result = []
		item = None

		for line in cmdres.output.split(b'\n'):
			if line.startswith(b'commit'):
				item = GitLog()
				item.commit = line.split(b' ')[1]
				result.append(item)
			elif line.startswith(b'Merge:'):
				item.merge = line[7:]
			elif line.startswith(b'Author:'):
				item.author = line[8:]
			elif line.startswith(b'Date:'):
				item.date = line[8:]
			elif line == b'':
				continue
			else:
				if item.description == None:
					item.description = line
				else:
					item.description += b'\n' + line
		
		return result

class GitTag:
	@staticmethod
	def parse(cmdres):
		result = cmdres.output.split(b'\n')		
		return result
		
class GitStatus:
	branch = ''
	staged = None
	not_staged = None
	untracked = None
	
	def __str__(self):
		string = 'branch: %s' %(str(self.branch))
		
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
			result.staged = []
			result.not_staged = []
			result.untracked = []

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
				elif b'HEAD detached at' in line:
					result.branch = line.split(b' ')[3]
			
		return result

class GitResetMode:
	Mixed = 0
	Soft = 1
	Hard = 2
	Merged = 3
	Keep = 4

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

	def checkout(self, target='', create_branch=False):
		result = None
		
		if target == b'':
			logger.error("Cannot checkout, target not provided")
		else:
			full_cmd = "git checkout"
			
			if create_branch:
				full_cmd = full_cmd + " -b"

			full_cmd = full_cmd + (" %s" %(target))

			logger.info(full_cmd)
			
			cmd = command.execute(full_cmd)
			
			if cmd.returncode != 0:
				logger.error("git checkout returned %s, code=%d", cmd.output, cmd.returncode)
			else:
				result = cmd.returncode
				
		return result

	def add(self, target=''):
		result = None
		
		if target == b'':
			logger.error("Cannot add, target not provided")
		else:
			full_cmd = "git add %s" %(target)
			
			logger.info(full_cmd)
			
			cmd = command.execute(full_cmd)
			
			if cmd.returncode != 0:
				logger.error("git add returned %s, code=%d", cmd.output, cmd.returncode)
			else:
				result = cmd.returncode
				
		return result

	def rm(self, target=''):
		result = None
		
		if target == b'':
			logger.error("Cannot rm, target not provided")
		else:
			full_cmd = "git rm %s" %(target)
			
			logger.info(full_cmd)
			
			cmd = command.execute(full_cmd)
			
			if cmd.returncode != 0:
				logger.error("git rm returned %s, code=%d", cmd.output, cmd.returncode)
			else:
				result = cmd.returncode
				
		return result

	def commit(self, message='', amend=False):
		result = None
		
		if message == b'' and amend == False:
			logger.error("Cannot commit, message not provided")
		else:
			full_cmd = "git commit"
			
			if amend:
				full_cmd = full_cmd + " --amend --no-edit"
			else:
				full_cmd = full_cmd + (" -m \"%s\"" %(message))
			
			logger.info(full_cmd)
			
			cmd = command.execute(full_cmd)
			
			if cmd.returncode != 0:
				logger.error("git commit returned %s, code=%d", cmd.output, cmd.returncode)
			else:
				result = cmd.returncode
				
		return result

	def log(self, n=1, author=None, branch=None, path=None):
		result = None
		
		if n <= 0:
			logger.error("Cannot query log, n is less or equal zero")
		else:
			full_cmd = "git log -n %d" %(n)
			
			if author != None:
				full_cmd = full_cmd + (" --author %s" %(author))
			
			if branch != None:
				full_cmd = full_cmd + (" -b %s" %(branch))
			
			if path != None:
				full_cmd = full_cmd + (" -- %s" %(path))
			
			logger.info(full_cmd)
			
			cmd = command.execute(full_cmd)
			
			if cmd.returncode != 0:
				logger.error("git log returned %s, code=%d", cmd.output, cmd.returncode)
			else:
				result = GitLog.parse(cmd)
				
		return result

	def pull(self, repo='origin', refspec=None):
		result = None
	
		full_cmd = "git pull %s" %(repo)
		
		if refspec != None:
			full_cmd = full_cmd + (" %s" %(refspec))
		
		logger.info(full_cmd)
		
		cmd = command.execute(full_cmd)
		
		if cmd.returncode != 0:
			logger.error("git pull returned %s, code=%d", cmd.output, cmd.returncode)
		
		result = cmd.returncode
		
		return result
		
	def push(self, repo='origin', refspec=None, set_upstream=False, force=False, tags=False):
		result = None
		
		full_cmd = "git push"
		
		if set_upstream:
			full_cmd = full_cmd + " --set-upstream"
			
		if force:
			full_cmd = full_cmd + " --force"
			
		if tags:
			full_cmd = full_cmd + " --tags"
		
		full_cmd = full_cmd + (" %s" %(repo))
		
		if refspec != None:
			full_cmd = full_cmd + (" %s" %(refspec))
		
		logger.info(full_cmd)
		
		cmd = command.execute(full_cmd)
		
		if cmd.returncode != 0:
			logger.error("git push returned: %s", str(cmd))
		
		result = cmd.returncode
		
		return result

	def branch(self, branch=None, set_upstream_to=None, set_upstream=False, unset_upstream=False, rename_to=None, delete=False):
		result = None
		
		full_cmd = "git branch"
		
		if set_upstream_to != None:
			if set_upstream_to == b'':
				full_cmd = None
				logger.error("git branch failed: set_upstream_to is invalid")
			else:
				full_cmd = full_cmd + (" --set-upstream-to=%s" %(set_upstream_to))
				if branch != None:
					full_cmd = full_cmd + (" %s" %(branch))
		elif unset_upstream:
			full_cmd = full_cmd + " --unset-upstream"
			if branch != None:
				full_cmd = full_cmd + (" %s" %(branch))
		elif rename_to != None:
			if rename_to == b'':
				full_cmd = None
				logger.error("git branch failed: rename_to value is invalid")
			else:
				full_cmd = full_cmd + (" -m %s" %(rename_to))
		elif delete:
			if branch == None or branch == b'':
				full_cmd = None
				logger.error("git branch delete failed: branch value is invalid")
			else:
				full_cmd = full_cmd + (" -D" %(branch))
		else:
			if branch == None:
				full_cmd = None
				logger.error("git branch failed: branch value is not provided")
			elif branch == b'':
				full_cmd = None
				logger.error("git branch failed: branch value is invalid")
			else:
				full_cmd = full_cmd + (" %s" %(branch))
		
		if full_cmd != None:
			logger.info(full_cmd)
			
			cmd = command.execute(full_cmd)
			
			if cmd.returncode != 0:
				logger.error("git branch returned: %s", str(cmd))
			
			result = cmd.returncode
		
		return result

	def reset(self, commit=None, mode=GitResetMode.Mixed):
		result = None
		
		full_cmd = "git reset"
		
		if mode == GitResetMode.Mixed:
			full_cmd = full_cmd + " --mixed"
		elif mode == GitResetMode.Soft:
			full_cmd = full_cmd + " --soft"
		elif mode == GitResetMode.Hard:
			full_cmd = full_cmd + " --hard"
		elif mode == GitResetMode.Merged:
			full_cmd = full_cmd + " --merged"
		elif mode == GitResetMode.Keep:
			full_cmd = full_cmd + " --keep"
		else:
			full_cmd = None
			logger.error("git reset failed: mode value is invalid")

		if full_cmd != None:
			if commit != None:
				full_cmd = full_cmd + (" %s" %(commit))
		
			logger.info(full_cmd)
			
			cmd = command.execute(full_cmd)
			
			if cmd.returncode != 0:
				logger.error("git reset returned: %s", str(cmd))
			
			result = cmd.returncode
		
		return result

	def remote(self, name=None, url=None, branch=None, prune=False, add=False, remove=False):
		result = None
		needs_parsing = False
		full_cmd = "git remote"
		
		if add:
			if name == None or url == None:
				logger.error("git remote failed: name and/or url value is invalid")
				full_cmd = None
			else:
				if branch != None:
					full_cmd += " -t %s" %(branch)
					
				full_cmd += " %s %s" %(name, url)
		elif remove:
			if name == None:
				logger.error("git remote failed: name value is invalid")
				full_cmd = None
			else:
				full_cmd += " remove %s" %(name)
		else:
			full_cmd += " -v"
			needs_parsing = True

		if full_cmd != None:
			logger.info(full_cmd)
			
			cmd = command.execute(full_cmd)
			
			if cmd.returncode != 0:
				logger.error("git remote returned: %s", str(cmd))
				result = cmd.returncode
			elif needs_parsing:
				result = GitRemote.parse(cmd)
			else:
				result = cmd.returncode

		return result

	def tag(self, tag=None, message=None, commit=None, annotate=False, add=False, delete=False):
		result = None
		parse_result = True

		full_cmd = "git tag"

		if add == True:
			if tag == None:
				full_cmd = None
				logger.error("git tag failed: tag value is invalid")
			else:
				if annotate == True:
					full_cmd += " -a"
				
				full_cmd += (" %s" %(tag))
				
				if commit != None:
					full_cmd += (" %s" %(commit))
				
				if message != None:
					full_cmd += (" -m \"%s\"" %(message))
					
				parse_result = False
		elif delete == True:
			if tag == None:
				full_cmd = None
				logger.error("git tag failed: tag value is invalid")
			else:
				full_cmd += (" -d %s" %(tag))
				parse_result = False
		else:
			full_cmd += " --list"
		
		if full_cmd != None:
			logger.info(full_cmd)
			
			cmd = command.execute(full_cmd)
			
			if cmd.returncode != 0:
				logger.error("git tag returned: %s", str(cmd))
			elif parse_result:
				result = GitTag.parse(cmd)
			else:
				result = cmd.returncode
		
		return result
		
	def merge(self):
		result = None
		return result

	def mv(self):
		result = None
		return result

	def init(self):
		result = None
		return result
		
	def setCredentials(self):
		result = None
		return result
		

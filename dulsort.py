#!/usr/bin/env python3

# Disk usage ls, sorted by size, human readable sizes

try:
  from itertools import zip_longest
  import os
  import pickle
  import re
  import subprocess
  import time
  import stat
except KeyboardInterrupt:
  exit()

# From
# https://stackoverflow.com/questions/287871/how-to-print-colored-text-in-terminal-in-python
# https://svn.blender.org/svnroot/bf-blender/trunk/blender/build_files/scons/tools/bcolors.py
class BackgroundColors:
  HEADER = '\033[95m'
  OKBLUE = '\033[94m'
  OKGREEN = '\033[92m'
  WARNING = '\033[93m'
  FAIL = '\033[91m'
  ENDC = '\033[0m'
  BOLD = '\033[1m'
  UNDERLINE = '\033[4m'

def toHumanReadableSize(kbSize):
  mb = kbSize / 1024.0
  gb = mb / 1024.0
  sm_fmt = '%.1f'
  lg_fmt = '%.0f'
  if gb > 1:
    if gb < 10:
      return (sm_fmt+'G') % gb
    return (lg_fmt+'G') % gb
  if mb > 1:
    if mb < 10:
      return (sm_fmt+'M') % mb
    return (lg_fmt+'M') % mb
  if kbSize < 10:
    return (sm_fmt+'K') % kbSize
  return (lg_fmt+'K') % kbSize

class MyFile:
  def __lt__(self, other):
    if other.kbSize is None:
      return True
    if self.kbSize is None:
      return False
    return self.kbSize < other.kbSize

  @property
  def isComputed(self):
    """Is it computed?"""
    return self.kbSize is not None

  @property
  def humanReadableSize(self):
    """Show kbSize nicely"""
    return toHumanReadableSize(self.kbSize)

  @property
  def isntSmall(self):
    return self.kbSize >= 1024.0

  def __init__(self, name, kbSizeStr=None):
    self.name = name
    [key, mtime] = getKeyAndMtime(name)
    self.mtime = mtime
    self.key = key
    self.kbSize = None
    if kbSizeStr is not None:
      self.setSize(kbSizeStr)

  def setSize(self, kbSizeStr):
    self.kbSize = int(kbSizeStr)

  def __str__(self):
    if isDirectory(self.name):
      decoratedName = BackgroundColors.OKBLUE + self.name + BackgroundColors.ENDC + '/'
    else:
      decoratedName = self.name
    if self.isComputed:
      return '%6s %s' % (self.humanReadableSize, decoratedName)
    else:
      return '...... %s' % (decoratedName)


def getKeyAndMtime(filename):
  stat_tuple = os.lstat(filename)
  key = str(stat_tuple.st_dev) + str(stat_tuple.st_ino)
  return [key, stat_tuple.st_mtime]

def isDirectory(filename):
  stat_tuple = os.lstat(filename)
  return stat.S_ISDIR(stat_tuple.st_mode)

SKIP_KB_REGEX = re.compile('([0-9\.]+)\t+(.*)')  # skip kilobyte and smaller


def runDuAndAddInfoTo(files):
  names = [f.name for f in files]
  try:
    output = subprocess.check_output(['du', '-ks', '--'] + names)
  except subprocess.CalledProcessError:
    output = subprocess.check_output(['sudo', 'du', '-ks', '--'] + names)
  for one_line in output.decode('utf-8').split('\n'):
    regexpMatch = SKIP_KB_REGEX.search(one_line)
    if regexpMatch is not None:
      matchGroups = regexpMatch.groups()
      (kbSizeStr, filename) = matchGroups
      file = [f for f in files if f.name == filename][0]
      file.setSize(kbSizeStr)


def grouper(n, iterable, padvalue=None):
  "grouper(3, 'abcdefg', 'x') --> ('a','b','c'), ('d','e','f'), ('g','x','x')"
  return zip_longest(*[iter(iterable)]*n, fillvalue=padvalue)


class Main:
  def __init__(self):
    home=os.environ['HOME']
    cacheFileAbsPath = os.path.join(home, 'Library', 'Caches', 'com.norsemind.dulsort-cache.pickle')
    try:
      self.cacheFile = open(cacheFileAbsPath, 'rb+')
      self.cache = pickle.load(self.cacheFile)
      self.cacheFile.seek(0)
      # print 'loaded cache, length is', len(self.cache)
    except (IOError, EOFError) as e:
      self.cacheFile=open(cacheFileAbsPath, 'wb')
      self.cache = {}
      # print 'made new cache'
    self.loadedCacheLen = len(self.cache)
    self.cacheHitCount = 0
    self.needsCleanup = False
    self.files = []

  def end(self):
    if self.cacheFile is not None:
      # print 'New items added to the cache: %d. Cache size now %d items. Cache hit count: %d' % (
      #     len(self.cache)-self.loadedCacheLen, len(self.cache), self.cacheHitCount)
      pickle.dump(self.cache, self.cacheFile)
      self.cacheFile.close()

  def getFromCache(self, filename):
    try:
      [key, mtime] = getKeyAndMtime(filename)
    except TypeError:
      key=None
    if key in self.cache:
      myFile = self.cache[key]
      if mtime == myFile.mtime:
        myFile.name = filename
        self.cacheHitCount += 1
        return myFile
      else:
        del self.cache[key]

  def duAndCacheAndPrint(self, files):
    for waitingFile in files:
      print(waitingFile)
    runDuAndAddInfoTo(files)
    for file in files:
      if file.key is not None:
        self.cache[file.key] = file
    self.displayCurses()

  def getCurrentDirFilesAndFolderNames(self):
    direct = os.walk('.').__next__()
    (thisDir, directories, files) = direct
    return directories + files

  def summonFile(self, filename):
    return self.getFromCache(filename) or MyFile(filename)

  def run(self):
    filenames = self.getCurrentDirFilesAndFolderNames()
    self.files = [self.summonFile(f) for f in filenames]
    scheduledForDiskusageRun = [f for f in self.files if not f.isComputed]
    chunks = grouper(3, scheduledForDiskusageRun)
    [self.duAndCacheAndPrint([f for f in chunk if f is not None]) for chunk in chunks]
    print('')
    os.system('cls' if os.name == 'nt' else 'clear')
    print('=========================')
    self.display()
    print('=========================')
    (a, b) = len(self.files), self.cacheHitCount
    percentage = int(b*100.0/a) if a is not 0 else 100
    print('total files: %d (cache hit: %d -- %d%%)' % \
      (a, b, percentage))
    print('total size: %s' % toHumanReadableSize(self.getTotalSize()))

  def getTotalSize(self):
    total = 0
    for myFile in self.files:
      total += myFile.kbSize
    return total

  def displayCurses(self):
    completed = [f for f in self.files if f.isComputed]
    terminal_line_count, _ = map(int, os.popen('stty size', 'r').read().split())
    emptyLineCount = terminal_line_count - len(completed)
    [print('') for i in range(emptyLineCount)]
    completed.sort()
    for myFile in completed[-terminal_line_count:]:
      print(myFile)

  def display(self):
    completed = [f for f in self.files if f.isComputed]
    terminal_line_count, _ = map(int, os.popen('stty size', 'r').read().split())
    completed.sort()
    for myFile in completed[-terminal_line_count:]:
      print(myFile)


if __name__ == '__main__':
  start=time.time()
  main = Main()
  try:
    main.run()
  except KeyboardInterrupt:
    print('')
  finally:
    main.end()
    end=time.time()
    print('total time spent:', end-start)



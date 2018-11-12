#!/usr/bin/env python3

# Disk usage ls, sorted by size, human readable sizes

try:
  import os
  import pickle
  import subprocess
  import re
  import time
except KeyboardInterrupt:
  exit()

class MyFile:
  def __lt__(self, other):
    return self.kbSize < other.kbSize

  def __init__(self):
    kbSize = None
    humanReadableSize = None
    name = None
    mtime = None
    key = None

  def __init__(self, kbSizeStr, name, mtime, key):
    kbSize = int(kbSizeStr)
    self.humanReadableSize = self.getHumanReadableSize(kbSize)
    self.mtime = mtime
    self.name = name
    self.kbSize = kbSize
    self.key = key

  def getHumanReadableSize(self, kbSize):
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

  def __str__(self):
    return '%6s %s' % (self.humanReadableSize, self.name)

  def __cmp__(self, myFile):
    return self.kbSize - myFile.kbSize


def getKeyAndMtime(filename):
  stat_tuple = os.lstat(filename)
  key = str(stat_tuple.st_dev) + str(stat_tuple.st_ino)
  return [key, stat_tuple.st_mtime]


def du(scheduledForDiskusageRun):
  files = []
  regexp = re.compile('([0-9\.]+)\s+(.*)')  # skip kilobyte and smaller
  try:
    output = subprocess.check_output(['du', '-ks', '--'] + scheduledForDiskusageRun)
  except subprocess.CalledProcessError:
    output = subprocess.check_output(['sudo', 'du', '-ks', '--'] + scheduledForDiskusageRun)
  for one_line in output.decode('utf-8').split('\n'):
    regexpMatch = regexp.search(one_line)
    if regexpMatch is not None:
      matchGroups = regexpMatch.groups()
      (kbSizeStr, name) = matchGroups
      [key, mtime] = getKeyAndMtime(name)
      myFile = MyFile(kbSizeStr, name, mtime, key)
      files.append(myFile)
  return files


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

  def end(self):
    if self.cacheFile is not None:
      # print 'New items added to the cache: %d. Cache size now %d items. Cache hit count: %d' % (
      #     len(self.cache)-self.loadedCacheLen, len(self.cache), self.cacheHitCount)
      pickle.dump(self.cache, self.cacheFile)
      self.cacheFile.close()

  def run(self):
    direct = os.walk('.').__next__()
    (thisDir, directories, files) = direct

    filesAndDirectories = directories + files
    filesAndDirectoriesCount = len(filesAndDirectories)
    progressString = ''
    scheduledForDiskusageRun = []
    myFileList=[]
    for index in range(filesAndDirectoriesCount):
      filename = filesAndDirectories[index]
      try:
        stat_tuple = os.lstat(filename)
        [key, mtime] = getKeyAndMtime(filename)
      except TypeError:
        key=None
      if key in self.cache:
        myFile = self.cache[key]
        if mtime == myFile.mtime:
          myFile.name = filename
          myFileList.append(myFile)
          self.cacheHitCount += 1
        else:
          del self.cache[key]
      if key not in self.cache:
        scheduledForDiskusageRun.append(filename)
      manyFilesCollected = len(scheduledForDiskusageRun) >= 3
      someFilesCollected = len(scheduledForDiskusageRun) > 0
      lastFileReached = index >= filesAndDirectoriesCount - 1
      mustRunDiskusage = (lastFileReached and someFilesCollected) or manyFilesCollected
      if mustRunDiskusage:
        self.display(myFileList)
        for waiting in scheduledForDiskusageRun:
          print('..... %s' % waiting)
        newMyFiles = du(scheduledForDiskusageRun)
        for file in newMyFiles:
          myFileList.append(file)
          if file.key is not None:
            self.cache[file.key] = file
        scheduledForDiskusageRun = []
        self.needsCleanup = True

    if self.needsCleanup:
      print('')
      os.system('cls' if os.name == 'nt' else 'clear')
    print('=========================')

    myFileList.sort()
    for myFile in myFileList:
      print(myFile)
    print('=========================')
    (a, b) = len(myFileList), self.cacheHitCount
    percentage = int(b*100.0/a) if a is not 0 else 100
    print('total files: %d (cache hit: %d -- %d%%)' % \
      (a, b, percentage))


  def display(self, myFileList):
    terminal_line_count, _ = map(
        int, os.popen('stty size', 'r').read().split())
    emptyLineCount = terminal_line_count - len(myFileList)
    myFileList.sort()
    for i in range(emptyLineCount):
      print('')
    for myFile in myFileList[-terminal_line_count:]:
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



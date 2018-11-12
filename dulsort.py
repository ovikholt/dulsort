#!/usr/bin/env python2.7

# Disk usage ls, sorted by size, human readable sizes

from __future__ import print_function

try:
  import os
  import cPickle
  import subprocess
  import re
  import time
except KeyboardInterrupt:
  exit()

class MyFile:
  def __init__(self):
    kbSize = None
    humanReadableSize = None
    name = None
    mtime = None

  def __init__(self, kbSizeStr, name, mtime):
    kbSize = int(kbSizeStr)
    self.humanReadableSize = self.getHumanReadableSize(kbSize)
    self.mtime = mtime
    self.name = name
    self.kbSize = kbSize

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


class Main:
  def __init__(self):
    home=os.environ['HOME']
    cacheFileAbsPath = os.path.join(home, 'Library', 'Caches', 'com.norsemind.dulsort-cache.pickle')
    try:
      self.cacheFile=open(cacheFileAbsPath, 'r+')
      self.cache = cPickle.load(self.cacheFile)
      self.cacheFile.seek(0)
      # print 'loaded cache, length is', len(self.cache)
    except (IOError, EOFError) as e:
      self.cacheFile=open(cacheFileAbsPath, 'w')
      self.cache = {}
      # print 'made new cache'
    self.loadedCacheLen = len(self.cache)
    self.cacheHitCount = 0
    self.needsCleanup = False

  def end(self):
    if self.cacheFile is not None:
      # print 'New items added to the cache: %d. Cache size now %d items. Cache hit count: %d' % (
      #     len(self.cache)-self.loadedCacheLen, len(self.cache), self.cacheHitCount)
      cPickle.dump(self.cache, self.cacheFile)
      self.cacheFile.close()

  def run(self):
    regexp=re.compile('([0-9\.]+)\s+(.*)')  # skip kilobyte and smaller
    direct = os.walk('.').next()
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
        key = str(stat_tuple.st_dev) + str(stat_tuple.st_ino)
        st_mtime = stat_tuple.st_mtime
      except TypeError:
        key=None
      if key in self.cache:
        myFile = self.cache[key]
        if st_mtime == myFile.mtime:
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
        diskusageStartTime = time.time()
        try:
          output = subprocess.check_output(['du', '-ks', '--'] + scheduledForDiskusageRun)
        except subprocess.CalledProcessError:
          output = subprocess.check_output(['sudo', 'du', '-ks', '--'] + scheduledForDiskusageRun)
        elapsedTime = time.time() - diskusageStartTime
        for one_line in output.split('\n'):
          regexpMatch = regexp.search(one_line)
          if regexpMatch is not None:
            matchGroups = regexpMatch.groups()
            (kbSizeStr, name) = matchGroups
            stat_tuple = os.lstat(name)
            key = str(stat_tuple.st_dev) + str(stat_tuple.st_ino)
            st_mtime = stat_tuple.st_mtime
            myFile = MyFile(kbSizeStr, name, st_mtime)
            myFileList.append(myFile)
            if key is not None:
              self.cache[key] = myFile
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



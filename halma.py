#!/usr/bin/env python
# *-----------------------------------------------------------------------*
# |                                                                       |
# |  Copyright (c) 2020 Thierry Zamofing (th.zamofing@gmail.com)        |
# |                                                                       |
# *-----------------------------------------------------------------------*
'''
Halma aka 'Chinese Checker' game
'''

import numpy as np
import logging
_log=logging.getLogger(__name__)
if __name__ == '__main__':
  logging.basicConfig(level=logging.DEBUG,format='%(levelname)s:%(module)s:%(lineno)d:%(funcName)s:%(message)s ')
  pass

class Halma:
  def __init__(self,numArmy=1):
    self.board=board=np.ndarray((17,17),dtype=np.uint8)
    br=board.ravel()
    br[:]=0x7#0x0f
    for i in range(13):#fill board
      board[i,4:5+i]=0

    startLst=(4,17*4+9,17*9+0xd,17*0xd+9,17*9+4,17*4) #start position of army
    for i in range(1,7):  # fill armies
      s=startLst[i-1]
      if i%2:
        #odd
        for j in range(1,5):
          br[s:s+j]=i
          s+=17
      else:
        #even
        for j in range(4,0,-1):
          br[s:s+j]=i
          s+=18

    self.armies=armies=np.ndarray((numArmy,17),dtype=np.uint16)
  def print(self,mode):
    board=self.board
    if mode==0:
      print(board)
    elif mode==1:
      s=board.shape
      for j in range(s[0]):
        ss = ' '*(17-j)
        for i in range(s[1]):
          k=board[j,i]
          if k==7: ss+='- '
          elif k==0: ss+='. '
          else: ss+='%d '%k
        print(ss)

if __name__ == '__main__':
  halma=Halma()
  halma.print(0)
  halma.print(1)

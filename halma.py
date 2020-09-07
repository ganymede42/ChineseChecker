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
  # start index position of each army (1-6) on the board
  armyStartIdxLst=np.array((4,17*4+9,17*9+0xd,17*0xd+9,17*9+4,17*4),dtype=np.uint16)

  @staticmethod
  def emptyboard():
    board=np.ndarray((17,17),dtype=np.uint8)
    br=board.ravel()
    br[:]=0x7#0x0f
    for i in range(13):#fill board
      board[i,4:5+i]=0
    startLst=Halma.armyStartIdxLst
    for i in (2,4,6):  # fill empty board locations for even armies
      s=startLst[i-1]
      for j in range(4,0,-1):
        br[s:s+j]=0
        s+=18
    return board

  def __init__(self):
    pass

  def Init(self, armyIdx=range(1,7)):
    self.board=halma.emptyboard()
    self.InitArmies(armyIdx)
    self.print(0)
    self.print(1)

  def InitArmies(self, armyIdx):
    halma.emptyboard()
    br=self.board.ravel()
    self.armiesIdx=armiesIdx=np.array(armyIdx)
    numArmy=armiesIdx.size
    self.armies=armies=np.ndarray((numArmy,10),dtype=np.uint16)
    startLst=Halma.armyStartIdxLst
    for i in range(numArmy):  # fill armies
      army=armies[i,:]
      armyIdx=armiesIdx[i]
      s=startLst[armyIdx-1]
      k=0
      if armyIdx%2:
        for j in range(1,5):#armyIdx is even odd army 1,3,5
          army[k:k+j]=s+np.array(range(j),dtype=np.uint16)
          k+=j
          s+=17
      else:
        for j in range(4, 0, -1):  # armyIdx is odd -> army 1,3,5
          army[k:k + j] = s + np.array(range(j), dtype=np.uint16)
          k += j
          s += 18
      br[army]=armyIdx
      #self.print(1)

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
          if k==7: ss+='  '#'- '
          elif k==0: ss+='. '
          else: ss+='%d '%k
        print(ss)

if __name__ == '__main__':
  #halma=Halma()
  halma=Halma()
  halma.Init()

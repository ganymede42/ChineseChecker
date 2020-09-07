#!/usr/bin/env python
# *-----------------------------------------------------------------------*
# |                                                                       |
# |  Copyright (c) 2020 Thierry Zamofing (th.zamofing@gmail.com)        |
# |                                                                       |
# *-----------------------------------------------------------------------*
'''
Halma aka 'Chinese Checker' game

value on board:
0: empty
1: army1
2: army2
3: army3
4: army4
5: army5
6: army6
7: out of board
8: move trace (in SeekLongMoves)
9: start man (in SeekLongMoves for debug)

verbose bits
 0x001 : init raw board
 0x002 : init nice board
 0x004 :
 0x008 :
 0x010 :
 0x020 :
 0x040 :
 0x080 :
 0x100 :
 0x200 :
 0x400 :
 0x800 :
'''

import numpy as np
np.set_printoptions(edgeitems=30, linewidth=100000, formatter=dict(float=lambda x: "%.3g" % x))
import logging
_log=logging.getLogger(__name__)
if __name__ == '__main__':
  logging.basicConfig(level=logging.DEBUG,format='%(levelname)s:%(module)s:%(lineno)d:%(funcName)s:%(message)s ')
  pass

class Halma:
  # start index position of each army (1-6) on the board
  # size= count of biggest army line: default 4 creates army of 4+3+2+1=10 man
  # armyLblStartLst has the first index in the board where where the is located

  def __init__(self,verbose=0,size=4):
    self.verbose=verbose
    self.size=size # size= count of biggest army line: default 4 creates army of 4+3+2+1=10 man
    self.armyLblStartLst=sil=np.ndarray(6,dtype=np.uint16)
    sz=size
    w=sz*4+1
    sil[0]=              sz
    sil[1]=w*sz        + 2*sz+1
    sil[2]=w*(2*sz+1)  + 3*sz+1
    sil[3]=w*(3*sz+1)  + 2*sz+1
    sil[4]=w*(2*sz+1)  + sz
    sil[5]=w*sz

  def Init(self, armyLbl=range(1,7)):
    verb=self.verbose
    self.board=self.emptyboard()
    self.InitArmies(armyLbl)
    self.InitWeightMap()
    if verb&0x01: self.print(0)
    if verb&0x02: self.print(1)

  def emptyboard(self,board=None):
    sz=self.size
    if board is None:
      board=np.ndarray((sz*4+1,sz*4+1),dtype=np.uint8)
    br=board.ravel()
    br[:]=0x7#0x0f
    for i in range(sz*3+1):#fill board
      board[i,sz:sz+1+i]=0
    startLst=self.armyLblStartLst
    w=sz*4+1+1
    for i in (2,4,6):  # fill empty board locations for even armies
      s=startLst[i-1]
      for j in range(sz,0,-1):
        br[s:s+j]=0
        s+=w
    return board

  def InitArmies(self, armyLbl,board=None):
    sz=self.size
    w=sz*4+1
    br=self.board.ravel()
    self.armiesLbl=armiesLbl=np.array(armyLbl)
    numArmy=armiesLbl.size
    armySz=sz*(sz+1)//2
    self.armies=armies=np.ndarray((numArmy,armySz),dtype=np.uint16)
    startLst=self.armyLblStartLst
    for i in range(numArmy):  # fill armies
      army=armies[i,:]
      armyLbl=armiesLbl[i]
      assert armyLbl>0 and armyLbl<=6,'army index must be in range 1..6'
      s=startLst[armyLbl-1]
      k=0
      if armyLbl%2:
        for j in range(1,sz+1):#armyLbl is even odd army 1,3,5
          army[k:k+j]=s+np.array(range(j),dtype=np.uint16)
          k+=j
          s+=w
      else:
        for j in range(sz, 0, -1):  # armyLbl is odd -> army 1,3,5
          army[k:k + j] = s + np.array(range(j), dtype=np.uint16)
          k += j
          s += w+1
      br[army]=armyLbl
      #self.print(1)

  @staticmethod
  def PlaceArmies(board, armies, armiesLbl):
    br=board.ravel()
    numArmy=armiesLbl.size
    for i in range(numArmy):  # fill armies
      armyLbl=armiesLbl[i]
      army=armies[i,:]
      br[army]=armyLbl

  def InitWeightMap(self):
    #MUST BE CALLED AFTER INITARMIES!!!
    sz=self.size
    shape=(self.armiesLbl.size,)+self.board.shape
    self.weightMap=wm=np.ndarray(shape=shape,dtype=np.uint16)
    #self.weightMap.ravel()[0:300]=range(300)
    wm[:]=0

    w=shape[1]
    a=np.arange(w,dtype=np.uint16)
    o=np.ones(w,dtype=np.uint16)
    d=np.fromfunction(lambda i,j:i+j,((w+1)//2,(w+1)//2),dtype=int)
    for idx,lbl in enumerate(self.armiesLbl):
      if lbl==1:
        wm[idx,:,:]=np.mat(a).T*np.mat(o)
      elif lbl==2:
        wm[idx,:,:]=0
        wm[idx,sz:w-sz,sz:w-sz]=np.fliplr(d)
      elif lbl==3:
        wm[idx,:,:]=a[::-1]
      elif lbl==4:
        wm[idx,:,:]=np.mat(a[::-1]).T*np.mat(o)
      elif lbl==5:
        wm[idx,:,:]=0
        wm[idx,sz:w-sz,sz:w-sz]=np.flipud(d)
      elif lbl==6:
        wm[idx,:,:]=a.T*o
      print(wm[idx,:,:])
      1
        #*anp.mat(a).T*np.mat(a)


  class Seek:
    def __init__(self,board):
      self.w=w=board.shape[0]
      self.br=br=board.ravel()
      self.maxIdx=w*w
      self.mv=mv=np.ndarray(shape=(br.size,2),dtype=np.uint16)  # allocate hopefully big enough array
      mv[:]=0  #for debug
      #'br' is the board on which moves are seeked
      #'mv' are the available move list

  def SeekMoves(self,armyIdx,board=None):
    if board is None: board=self.board
    # a b
    # c . d
    #   e f
    #Possible short moves:  =a=-18   b=-17   c=-1   d=+1   e=+17   f=+18
    #Possible jump moves:   =a=-2*18 b=-2*17 c=-1*2 d=+1*2 e=+17*2 f=+18*2
    army=self.armies[armyIdx,:]
    i=0

    seek=Halma.Seek(board)
    w=seek.w;maxIdx=seek.maxIdx;br=seek.br;mv=seek.mv
    armyLbl=br[army[0]]
    for man in army:
      #TODO:resize moves if needed
      br[man]=9; #self.print(1)
      js=i
      #short moves:
      p=man-w-1
      if p>0 and not br[p]: mv[i,:]=(man,p);i+=1
      p=man-w
      if p>0 and not br[p]: mv[i,:]=(man,p);i+=1
      p=man-1
      if p>0 and not br[p]: mv[i,:]=(man,p);i+=1
      p=man+1
      if p<maxIdx and not br[p]: mv[i,:]=(man,p);i+=1
      p=man+w
      if p<maxIdx and not br[p]: mv[i,:]=(man,p);i+=1
      p=man+w+1
      if p<maxIdx and not br[p]: mv[i,:]=(man,p);i+=1
      #long mv:
      if i>js:
        print('short moves',mv[js:i,:])
      jl=i
      i=Halma.SeekLongMoves(seek, man, man, i)
      if i>jl:
        print('long moves',mv[jl:i,:])
      if i>js:
        br[mv[js:jl,1]]=0xa
        self.print(1)
        br[mv[js:i,1]]=0
      br[man]=armyLbl

  @staticmethod
  def SeekLongMoves(seek,man,pcur,i):
    w=seek.w;maxIdx=seek.maxIdx;br=seek.br;mv=seek.mv
    w2=2*w
    #TODO:resize mv if needed
    p1=pcur-w-1; p2=pcur-w2-2
    if p2>0 and br[p1]>0 and br[p1]<=6 and not br[p2]: mv[i,:]=(man,p);br[p]=8;i=Halma.SeekLongMoves(seek,man,p2,i+1)
    p1=pcur-w  ; p2=pcur-w2
    if p2>0 and br[p1]>0 and br[p1]<=6 and not br[p2]: mv[i,:]=(man,p);br[p]=8;i=Halma.SeekLongMoves(seek,man,p2,i+1)
    p1=pcur-1  ; p2=pcur-2
    if p2>0 and br[p1]>0 and br[p1]<=6 and not br[p2]: mv[i,:]=(man,p);br[p]=8;i=Halma.SeekLongMoves(seek,man,p2,i+1)
    p1=pcur+1  ; p2=pcur+2
    if p2<maxIdx and br[p1]>0 and br[p1]<=6 and not br[p2]: mv[i,:]=(man,p);br[p]=8;i=Halma.SeekLongMoves(seek,man,p2,i+1)
    p1=pcur+w  ; p2=pcur+w2
    if p2<maxIdx and br[p1]>0 and br[p1]<=6 and not br[p2]: mv[i,:]=(man,p2);br[p2]=8;i=Halma.SeekLongMoves(seek,man,p2,i+1)
    p1=pcur+w+1; p2=pcur+w2+2
    if p2<maxIdx and br[p1]>0 and br[p1]<=6 and not br[p2]: mv[i,:]=(man,p2);br[p2]=8;i=Halma.SeekLongMoves(seek,man,p2,i+1)
    return i

  def print(self,mode):
    board=self.board
    if mode==0:
      print(board)
    elif mode==1:
      s=board.shape
      sz=self.size
      w=sz*4+1
      ofs=sz*3+1
      for j in range(s[0]):
        ss = ' '*(w-j)
        for i in range(s[1]):
          k=board[j,i]
          if k==7: ss+='  '#'- '
          elif k==0: ss+='. '
          else: ss+='%.2x'%k
        print(ss[ofs:])

if __name__ == '__main__':
  halma=Halma(verbose=0xff)
  #halma=Halma(5)
  #halma.Init()
  #halma.Init([2,5])
  halma.Init([1,2])
  #halma.SeekMoves(armyIdx=0)

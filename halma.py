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
8: long move final points and move trace (in SeekLongMoves)
9: start man (in SeekLongMoves for debug)
a: short move final point
verbose bits
 0x001 : init board
 0x002 : weight map
 0x004 : show all possible moves
 0x008 : show moves in function Halma.Move()
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

  def __init__(self,verbose=0xff,printMode=0x3,size=4):
    self.verbose=verbose
    self.printMode=printMode
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
    if verb&0x01: self.printBrd(0x3)

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

  def InitWeightMap(self,mode=0):
    #MUST BE CALLED AFTER INITARMIES!!!
    verb=self.verbose
    sz=self.size
    brd=self.board
    oobIdx=np.where(brd.ravel()==7)
    shape=(self.armiesLbl.size,)+brd.shape
    self.weightMap=wms=np.ndarray(shape=shape,dtype=np.uint16)
    #self.weightMap.ravel()[0:300]=range(300)
    wms[:]=0
    w=shape[1]
    if mode==0:#linear distance to goal
      a=np.arange(w,dtype=np.uint16)+1
      o=np.ones(w,dtype=np.uint16)
      d=np.fromfunction(lambda i,j:i+j-2*sz+1,(w,w),dtype=int)
    elif mode==1:#linear + inverse progressive distance to goal
      a=np.arange(w,dtype=np.uint16)
      a+a[::-1].cumsum()/8
      o=np.ones(w,dtype=np.uint16)
      d=np.fromfunction(lambda i,j:i+j-2*sz,(w,w),dtype=int)

    for idx,lbl in enumerate(self.armiesLbl):
      wm=wms[idx,:,:]
      if lbl==1:
        wm[:,:]=np.mat(a).T*np.mat(o)
      elif lbl==2:
        wm[:,:]=np.fliplr(d)
      elif lbl==3:
        wm[:,:]=a[::-1]
      elif lbl==4:
        wm[:,:]=np.mat(a[::-1]).T*np.mat(o)
      elif lbl==5:
        wm[:,:]=np.flipud(d)
      elif lbl==6:
        wm[:,:]=a.T*o
      wm[:,:].ravel()[oobIdx]=0
      if verb&0x02: self.printBrd(0x5,wms[idx,:,:])
      1

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
    verb=self.verbose
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
    #for man in army:
    for man,manIdx in enumerate(army):
      #TODO:resize moves if needed
      br[man]=9; #self.print(1)
      js=i
      #short moves:
      p=man-w-1
      if p>0 and not br[p]: mv[i,:]=(manIdx,p);i+=1
      p=man-w
      if p>0 and not br[p]: mv[i,:]=(manIdx,p);i+=1
      p=man-1
      if p>0 and not br[p]: mv[i,:]=(manIdx,p);i+=1
      p=man+1
      if p<maxIdx and not br[p]: mv[i,:]=(manIdx,p);i+=1
      p=man+w
      if p<maxIdx and not br[p]: mv[i,:]=(manIdx,p);i+=1
      p=man+w+1
      if p<maxIdx and not br[p]: mv[i,:]=(manIdx,p);i+=1
      #long mv:
      jl=i
      seek.manIdx=maxIdx
      i=Halma.SeekLongMoves(seek, man, man, i)

      if i>js:
        if verb&0x04 and i>js:
          print('%d short %d long moves'%(jl-js,i-jl))
          print(mv[js:i,:].T)
          br[mv[js:jl,1]]=0xa
          self.printBrd(0x3)
        br[mv[js:i,1]]=0
      br[man]=armyLbl

  @staticmethod
  def SeekLongMoves(seek,man,pcur,i):
    w=seek.w;maxIdx=seek.maxIdx;br=seek.br;mv=seek.mv;maxIdx=seek.maxIdx
    w2=2*w
    #TODO:resize mv if needed
    p1=pcur-w-1; p2=pcur-w2-2
    if p2>0 and br[p1]>0 and br[p1]<=6 and not br[p2]: mv[i,:]=(maxIdx,p2);br[p2]=8;i=Halma.SeekLongMoves(seek,man,p2,i+1)
    p1=pcur-w  ; p2=pcur-w2
    if p2>0 and br[p1]>0 and br[p1]<=6 and not br[p2]: mv[i,:]=(maxIdx,p2);br[p2]=8;i=Halma.SeekLongMoves(seek,man,p2,i+1)
    p1=pcur-1  ; p2=pcur-2
    if p2>0 and br[p1]>0 and br[p1]<=6 and not br[p2]: mv[i,:]=(maxIdx,p2);br[p2]=8;i=Halma.SeekLongMoves(seek,man,p2,i+1)
    p1=pcur+1  ; p2=pcur+2
    if p2<maxIdx and br[p1]>0 and br[p1]<=6 and not br[p2]: mv[i,:]=(maxIdx,p2);br[p2]=8;i=Halma.SeekLongMoves(seek,man,p2,i+1)
    p1=pcur+w  ; p2=pcur+w2
    if p2<maxIdx and br[p1]>0 and br[p1]<=6 and not br[p2]: mv[i,:]=(maxIdx,p2);br[p2]=8;i=Halma.SeekLongMoves(seek,man,p2,i+1)
    p1=pcur+w+1; p2=pcur+w2+2
    if p2<maxIdx and br[p1]>0 and br[p1]<=6 and not br[p2]: mv[i,:]=(maxIdx,p2);br[p2]=8;i=Halma.SeekLongMoves(seek,man,p2,i+1)
    return i

  def Move(self,armyIdx,manIdx,dspPos,board=None):
    if board is None: board=self.board
    bd=board.ravel()
    army=self.armies[armyIdx,:]
    lbl=self.armiesLbl[armyIdx]
    bdIdx=army[manIdx]
    assert bd[bdIdx]==lbl,'move error on that board'
    bd[bdIdx]=0
    army[manIdx]=dspPos
    bd[dspPos]=lbl
    if self.verbose&0x08:
      self.printBrd(0x3)

  def printBrd(self,mode,board=None):
    if board is None:
      board=self.board
    if mode&1:
      print(board)
    if mode&2:
      s=board.shape
      sz=self.size
      w=sz*4
      ofsS=sz*3*1
      ofsE=sz*3*1+(sz*3+1)*2
      for j in range(s[0]):
        ss = ' '*(w-j)
        for i in range(s[1]):
          k=board[j,i]
          if k==7: ss+='  '#'+-'
          elif k==0: ss+=' .'#'cd'
          else: ss+='%2.x'%k
        print(ss[ofsS:ofsE])
    if mode&4:
      s=board.shape
      sz=self.size
      w=sz*4
      ofsS=sz*3*3
      ofsE=sz*3*3+(sz*3+1)*6
      #width of element has to be even: here it is 6
      for j in range(s[0]):
        ss = '   '*(w-j) #half width of element (3)
        for i in range(s[1]):
          k=board[j,i]
          if k==0: ss+='      '#'+    -'
          else: ss+='%6.5g'%(k)
          #else: ss+='+%4.3g-'%(k*10.123)
        print(ss[ofsS:ofsE])

if __name__ == '__main__':
  v=0xff
  v=0xf3
  #v=0x02
  halma=Halma(verbose=v,printMode=0x3)
  #halma=Halma(verbose=v,printMode=0x3,size=5)
  #halma.Init()
  #halma.Init([2,5])
  #halma.Init([1,2])
  #halma.SeekMoves(armyIdx=0)

  halma.Init([1,])
  halma.Move(0,0,17*5+6)
  halma.SeekMoves(armyIdx=0)


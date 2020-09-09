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
 0x004 : show all possible moves Halma.SeekMoves()
 0x008 : show moves quality in  Halma.EvalMoves()
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
import ctypes as ct
np.set_printoptions(edgeitems=30, linewidth=100000, precision=2)
#np.set_printoptions(edgeitems=30, linewidth=100000, formatter=dict(float=lambda x: "%.3g" % x))
import logging
_log=logging.getLogger(__name__)
if __name__ == '__main__':
  logging.basicConfig(level=logging.DEBUG,format='%(levelname)s:%(module)s:%(lineno)d:%(funcName)s:%(message)s ')


#C-types array structures for searching tree
#--------------------------------------------
#https://stackoverflow.com/questions/40063080/casting-an-array-of-c-structs-to-a-numpy-array
#https://numpy.org/doc/stable/user/basics.rec.html
#https://numpy.org/doc/stable/reference/generated/numpy.ndarray.ctypes.html?highlight=ctypes#numpy.ndarray.ctypes
>>> class POINT(Structure):
...     _fields_ = [("x", c_int),
...                 ("y", c_int)]
.


class InfoC(ct.Structure):
     _fields_ = [('armies',     ct.POINTER(ct.c_uint16)),
     _fields_ = [('armiesLbl',  ct.POINTER(ct.c_uint8)),
     _fields_ = [('numArmies',  ct.c_uint8),
     _fields_ = [('lenArmy',    ct.c_uint8),
     _fields_ = [('board',      ct.POINTER(ct.c_uint8)),
     _fields_ = [('weightmaps', ct.POINTER(ct.c_float)),
     _fields_ = [('distmap',    ct.POINTER(ct.c_uint8)),
     _fields_ = [('w',          ct.uint8)]


tSeekManC=np.dtype([('manIdx',np.uint8),('dstPos',np.uint16),('quality',np.float)],align=True)
tSeekArmyC=np.dtype([('armyIdx',np.uint8),('moves',tSeekManC, (128,)),('lenUsedMoves',np.uint8)],align=True)
SeekTreeC=np.dtype([('bestQuality',np.float),('bestIdx',np.uint8)],align=True)
#x=np.array([(2,3,4)],dtype=tSeekManC)
#np.ndarray(shape=(1,),dtype=tSeekArmyC)
#np.empty(shape=(1,),dtype=tSeekArmyC)
#np.zeros(shape=(1,),dtype=tSeekArmyC)




class Halma:
  # start index position of each army (1-6) on the board
  # size= count of biggest army line: default 4 creates army of 4+3+2+1=10 man
  # armyLblStartLst has the first index in the board where where the is located

  def __init__(self,verbose=0xff,size=4):
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
    if verb&0x01: self.printBrd(0x3)

  def emptyboard(self,board=None):
    sz=self.size
    if board is None:
      board=np.ndarray((sz*4+1,sz*4+1),dtype=np.uint8)
    bd=board.ravel()
    bd[:]=0x7#0x0f
    for i in range(sz*3+1):#fill board
      board[i,sz:sz+1+i]=0
    startLst=self.armyLblStartLst
    w=sz*4+1+1
    for i in (2,4,6):  # fill empty board locations for even armies
      s=startLst[i-1]
      for j in range(sz,0,-1):
        bd[s:s+j]=0
        s+=w
    return board

  def InitArmies(self, armyLbl,board=None):
    sz=self.size
    w=sz*4+1
    bd=self.board.ravel()
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
      bd[army]=armyLbl
      #self.print(1)

  @staticmethod
  def PlaceArmies(board, armies, armiesLbl):
    bd=board.ravel()
    numArmy=armiesLbl.size
    for i in range(numArmy):  # fill armies
      armyLbl=armiesLbl[i]
      army=armies[i,:]
      bd[army]=armyLbl

  def InitWeightMap(self,mode=0):
    #MUST BE CALLED AFTER INITARMIES!!!
    verb=self.verbose
    sz=self.size
    bd=self.board
    usedIdx=np.nonzero(bd!=7)
    shape=(self.armiesLbl.size,)+bd.shape
    self.weightMap=wms=np.ndarray(shape=shape,dtype=np.float)
    self.distMap=dms=np.ndarray(shape=shape,dtype=np.uint8)
    wms[:]=0;dms[:]=0
    w=shape[1]

    o=np.ones(w,dtype=np.float)
    a=np.arange(w,dtype=np.float)+1
    dm2d=np.asarray(np.mat(a).T*np.mat(o))

    #inverse progressive distance to goal
    a=(a+a[::-1].cumsum()/4)
    a/=a[0]
    wm2d=np.asarray(np.mat(a).T*np.mat(o))
    #penalize non central
    nctr=np.fromfunction(lambda y,x:np.abs(2*(x-sz)-y),(w,w),dtype=int)
    wm2d-=nctr*.3 #.25 seems better but cant finish without prediction



    wm1d=wm2d[usedIdx]
    dm1d=dm2d[usedIdx]

    #testing ascending weight array
    #wm1d=np.arange(1,usedIdx[0].size+1)
    #tweak some values:
    wm1d[104]=wm1d[102]

    #-------- setting up sort arrays --------
    itlx=np.arange(w*w,dtype=int).reshape(w,w)
    itly=itlx.T
    iblx=itlx[::-1,:]
    itrx=itlx[:,::-1]
    ibrx=itlx[::-1,::-1]
    ibly=itly[::-1,:]
    itry=itly[:,::-1]
    ibry=itly[::-1,::-1]
    #wm=wms[0,:,:]
    #wm[usedIdx]=wm1d[np.argsort(itlx[usedIdx])];self.printBrd(0x5,wm)#1
    #wm[usedIdx]=wm1d[np.argsort(itly[usedIdx])];self.printBrd(0x5,wm)#6-
    #wm[usedIdx]=wm1d[np.argsort(iblx[usedIdx])];self.printBrd(0x5,wm)#4
    #wm[usedIdx]=wm1d[np.argsort(itrx[usedIdx])];self.printBrd(0x5,wm)#1-
    #wm[usedIdx]=wm1d[np.argsort(ibrx[usedIdx])];self.printBrd(0x5,wm)#4-
    #wm[usedIdx]=wm1d[np.argsort(ibly[usedIdx])];self.printBrd(0x5,wm)#2
    #wm[usedIdx]=wm1d[np.argsort(itry[usedIdx])];self.printBrd(0x5,wm)#-5
    #wm[usedIdx]=wm1d[np.argsort(ibry[usedIdx])];self.printBrd(0x5,wm)#-3
    for idx,lbl in enumerate(self.armiesLbl):
      wm=wms[idx,:,:]
      dm=dms[idx,:,:]
      if lbl==1:
        wm[usedIdx]=wm1d[np.argsort(itlx[usedIdx])]#1
        dm[usedIdx]=dm1d[np.argsort(itlx[usedIdx])]#1
      elif lbl==2:
        wm[usedIdx]=wm1d[np.argsort(ibly[usedIdx])]
        dm[usedIdx]=dm1d[np.argsort(ibly[usedIdx])]
      elif lbl==3:
        wm[usedIdx]=wm1d[np.argsort(ibry[usedIdx])]
        dm[usedIdx]=dm1d[np.argsort(ibry[usedIdx])]
      elif lbl==4:
        wm[usedIdx]=wm1d[np.argsort(iblx[usedIdx])]#4
        dm[usedIdx]=dm1d[np.argsort(iblx[usedIdx])]#4
      elif lbl==5:
        wm[usedIdx]=wm1d[np.argsort(itry[usedIdx])]#5
        dm[usedIdx]=dm1d[np.argsort(itry[usedIdx])]#5
      elif lbl==6:
        wm[usedIdx]=wm1d[np.argsort(itly[usedIdx])]#6
        dm[usedIdx]=dm1d[np.argsort(itly[usedIdx])]#6
      #wm[:,:].ravel()[oobIdx]=0
      if verb&0x02:
        self.printBrd(0x5,wms[idx,:,:])
        self.printBrd(0x5,dms[idx,:,:])
      #print(lbl)
      #1

  def Run(self):
    '''press:
 x: quit
 h: help
 w: weight map
 t: treesearch
 b: best move (depth 1)'''
    print(Halma.Run.__doc__)
    i=0
    while True:
      k=getkey()
      if k=='x':   break
      elif k=='h': print(Halma.Run.__doc__)
      elif k=='b':#do best computer move depth=1
        skNd=self.SeekMoves(armyIdx=0)
        self.EvalMoves(skNd)
        q=self.ExecBestMove(skNd) #quality
        posSum=self.distMap[0].ravel()[self.armies[0]].sum() #positional sum
        print('move %d quality:%g, posSum: %d, press key'%(i,q,posSum))
        if posSum==150:
          print('Finished!, press key')
          break
        i+=1
      elif k=='t':  #do best computer move depth=n
        self.SeekTreeMove(depth=3,reduce=3)
      elif k=='s':#show moves
        skNd=self.SeekMoves(armyIdx=0)
        self.EvalMoves(skNd)
        self.ShowSeekNode(skNd)
      elif k=='w':#show weight map
        self.printBrd(0x5,self.weightMap[0,:,:])
        self.printBrd(0x5,self.distMap[0,:,:])
        pass


  class SeekNode:
    def __init__(self,halma,armyIdx):
      #---constants of whole seek---
      board=halma.board
      self.w=w=board.shape[0]
      self.bd=bd=board.ravel()
      self.maxIdx=w*w
      l=bd.size
      #---node moves and quality---
      #mv is the possible moves array (manIdx, finamlBrdIdx)
      #mvQ is the quality evaluation of the move
      self.armyIdx=armyIdx
      self.army=halma.armies[armyIdx,:]
      self.armyLbl=armyLbl=halma.armiesLbl[armyIdx]

      self._mvRaw=mv=np.ndarray(shape=(l,2),dtype=np.uint16)  # allocate hopefully big enough array
      self._mvRawQ=mvQ=np.ndarray(shape=(l),dtype=np.float)  # allocate hopefully big enough array
      #_mvRaw,_mvRawQ is the whole array mv,mvQ is a view that is resized
      mv[:]=0  #for debug
      mvQ[:]=0  #for debug
      #'bd' is the board on which moves are seeked
      #'mv' are the available move list

  def SeekMoves(self,armyIdx,board=None):
    verb=self.verbose
    if board is None: board=self.board
    # a b
    # c . d
    #   e f
    #Possible short moves:  =a=-18   b=-17   c=-1   d=+1   e=+17   f=+18
    #Possible jump moves:   =a=-2*18 b=-2*17 c=-1*2 d=+1*2 e=+17*2 f=+18*2
    i=0
    skNd=Halma.SeekNode(self,armyIdx)
    skArmy=np.zeros((1,),tSeekArmyC)
    #skArmy[0]['armyIdx']; x=skArmy[0]; x['armyIdx']; x.dtype

    w=skNd.w;maxIdx=skNd.maxIdx;bd=skNd.bd;mv=skNd._mvRaw
    armyLbl=skNd.armyLbl;army=skNd.army
    #armyLbl=bd[self.army[0]]
    #for man in army:
    for manIdx,man in enumerate(army):
      #TODO:resize moves if needed
      bd[man]=9; #self.print(1)
      js=i
      #short moves:
      p=man-w-1
      if p>0 and not bd[p]: mv[i,:]=(manIdx,p);i+=1
      p=man-w
      if p>0 and not bd[p]: mv[i,:]=(manIdx,p);i+=1
      p=man-1
      if p>0 and not bd[p]: mv[i,:]=(manIdx,p);i+=1
      p=man+1
      if p<maxIdx and not bd[p]: mv[i,:]=(manIdx,p);i+=1
      p=man+w
      if p<maxIdx and not bd[p]: mv[i,:]=(manIdx,p);i+=1
      p=man+w+1
      if p<maxIdx and not bd[p]: mv[i,:]=(manIdx,p);i+=1
      #long mv:
      jl=i
      skNd.manIdx=manIdx
      i=Halma.SeekLongMoves(skNd, man, man, i)

      if i>js:
        if verb&0x04 and i>js:
          print('%d short %d long moves'%(jl-js,i-jl))
          print(mv[js:i,:].T)
          bd[mv[js:jl,1]]=0xa
          self.printBrd(0x2)
        bd[mv[js:i,1]]=0
      bd[man]=armyLbl
    skNd.mv=skNd._mvRaw[:i,:]# view of _mvRaw object with correct size
    skNd.mvQ=skNd._mvRawQ[:i]# view of _mvRawQ object with correct size
    return skNd

  def ExecBestMove(self,skNd):
    mv=skNd.mv;mvQ=skNd.mvQ;army=skNd.army
    best=np.argmax(mvQ)
    manIdx,dspPos=mv[best,:]
    self.Move(army,manIdx,dspPos,verb=True)
    return mvQ[best]

  @staticmethod
  def SeekLongMoves(seek,man,pcur,i):
    w=seek.w;maxIdx=seek.maxIdx;bd=seek.bd;mv=seek._mvRaw;manIdx=seek.manIdx
    w2=2*w
    #TODO:resize mv if needed
    p1=pcur-w-1; p2=pcur-w2-2
    if p2>0 and bd[p1]>0 and bd[p1]<=6 and not bd[p2]: mv[i,:]=(manIdx,p2);bd[p2]=8;i=Halma.SeekLongMoves(seek,man,p2,i+1)
    p1=pcur-w  ; p2=pcur-w2
    if p2>0 and bd[p1]>0 and bd[p1]<=6 and not bd[p2]: mv[i,:]=(manIdx,p2);bd[p2]=8;i=Halma.SeekLongMoves(seek,man,p2,i+1)
    p1=pcur-1  ; p2=pcur-2
    if p2>0 and bd[p1]>0 and bd[p1]<=6 and not bd[p2]: mv[i,:]=(manIdx,p2);bd[p2]=8;i=Halma.SeekLongMoves(seek,man,p2,i+1)
    p1=pcur+1  ; p2=pcur+2
    if p2<maxIdx and bd[p1]>0 and bd[p1]<=6 and not bd[p2]: mv[i,:]=(manIdx,p2);bd[p2]=8;i=Halma.SeekLongMoves(seek,man,p2,i+1)
    p1=pcur+w  ; p2=pcur+w2
    if p2<maxIdx and bd[p1]>0 and bd[p1]<=6 and not bd[p2]: mv[i,:]=(manIdx,p2);bd[p2]=8;i=Halma.SeekLongMoves(seek,man,p2,i+1)
    p1=pcur+w+1; p2=pcur+w2+2
    if p2<maxIdx and bd[p1]>0 and bd[p1]<=6 and not bd[p2]: mv[i,:]=(manIdx,p2);bd[p2]=8;i=Halma.SeekLongMoves(seek,man,p2,i+1)
    return i

  def EvalMoves(self,seek):
    bd=seek.bd;mv=seek.mv;mvQ=seek.mvQ;armyIdx=seek.armyIdx
    verb=self.verbose&0x08
    army=seek.army
    numMv=mv.shape[0]
    #print('%d moves'%numMv)
    #print(mv.T)
    wm=self.weightMap[armyIdx].ravel()
    dm=self.distMap[armyIdx].ravel()
    for k in range(numMv):
      manIdx,dspPos=mv[k,:]
      srcPos=self.Move(army,manIdx,dspPos,verb=verb)
      mvQ[k]=wm[army].sum()
      #maxDiff=np.diff(np.sort(army)).max()/seek.w
      maxDiff=np.diff(np.sort(dm[army])).max()
      if maxDiff>2:
        mvQ[k]-=maxDiff*1.
      if verb: print(mvQ[k])
      self.Move(army,manIdx,srcPos)

  def ShowSeekNode(self,skNd):
    bd=skNd.bd;mv=skNd.mv;mvQ=skNd.mvQ;armyIdx=skNd.armyIdx
    verb=self.verbose&0x08
    army=skNd.army
    numMv=mv.shape[0]
    print('%d moves'%numMv)
    print(np.vstack((mv.T,mvQ.T)))

  def Move(self,army,manIdx,dspPos,board=None,verb=False):
    if board is None: board=self.board
    bd=board.ravel()
    srcPos=army[manIdx]
    lbl=bd[srcPos]
    bd[srcPos]=0
    army[manIdx]=dspPos
    bd[dspPos]=lbl
    if verb:
      self.printBrd(0x2)#0x03
    return srcPos

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

  def RunSeekTree(self, depth=3, reduce=3):
    #depth= search deph levels
    #reduce = maximal children per node
    skNd=self.SeekMoves(armyIdx=0)
    self.EvalMoves(skNd)

    #self
    #SeekTreeMove(self,skNdParent,depth=3,reduce=3)
    pass

  def SeekTreeMove(self, skNdParent, depth=3, reduce=3):
    #depth= search deph levels
    #reduce = maximal children per node
    skNd=self.SeekMoves(armyIdx=0)
    self.EvalMoves(skNd)

    pass

if __name__ == '__main__':

  #terup terminal not to buffer until EOL
  try:
    import sys,termios
    fd=sys.stdin.fileno()
    new=termios.tcgetattr(fd)
    #When ICANON is set, the terminal buffers a line at a time, and enables line editing.
    #Without ICANON, input is made available to programs immediately
    new[3]=new[3]&~termios.ICANON  # lflags
    termios.tcsetattr(fd,termios.TCSADRAIN,new)
  except termios.error as e:
    print("can't setup termios")

  def getkey():
    k=sys.stdin.read(1)
    return k[0]

  def main():
    #v=0xffff
    v=0x03
    #v=0xf3
    #v=0x02
    halma=Halma(verbose=v)
    #halma=Halma(verbose=v,size=5)
    #halma.Init();exit(0)
    #halma.Init([1,4,5,6]);exit(0)
    #halma.Init([2,5])
    #halma.Init([1,2])
    #halma.SeekMoves(armyIdx=0)

    halma.Init([1,])
    #srcPos=halma.Move(halma.armies[0],0,17*5+6,verb=True)
    print('Initialization done, press key')
    halma.Run()
  main()

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
 0x010 : debug SeekTreeRoot
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

#define global types also for C-interfacing
class ctInfo(ct.Structure):
  _fields_=[('armies',     ct.POINTER(ct.c_uint16)),
            ('armiesLbl',  ct.POINTER(ct.c_uint8)),
            ('numArmies',  ct.c_uint8),
            ('lenArmy',    ct.c_uint8),
            ('board',      ct.POINTER(ct.c_uint8)),
            ('weightmaps', ct.POINTER(ct.c_float)),
            ('distmap',    ct.POINTER(ct.c_uint8)),
            ('w',          ct.c_uint8)]

dtSeekMan=np.dtype([('manIdx',np.uint8),('dstPos',np.uint16),('quality',np.float)],align=True)
dtSeekArmy=np.dtype([('armyIdx',np.uint8),('moves',dtSeekMan, (128,)),('numMoves',np.uint8)],align=True)
dtSeekTree=np.dtype([('bestQuality',np.float),('bestIdx',np.uint8)],align=True)



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

  def Init(self, armyLbl=range(1,7),armyIdxAI=(),armyIdxFirst=0):
    verb=self.verbose
    self.board=self.emptyboard()
    self.InitArmies(armyLbl,armyIdxAI,armyIdxFirst)
    self.InitWeightMap()
    if verb&0x01: self.printBrd(0x1b)#(0x3)

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

  def InitArmies(self,armyLbl,armyIdxAI,armyIdxFirst):
    sz=self.size
    w=sz*4+1
    bd=self.board.ravel()
    self.armiesLbl=armiesLbl=np.array(armyLbl,np.uint8)
    self.armyIdxAI=armyIdxAI=np.array(armyIdxAI,np.uint8)
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
    if armyIdxFirst>0:
      self.armiesLbl=np.roll(armiesLbl,-armyIdxFirst,0)
      self.armyIdxAI=(armyIdxAI+(numArmy-armyIdxFirst))%numArmy
      self.armies=np.roll(armies,-armyIdxFirst,0)
    #print(self.armiesLbl)
    #print(self.armyIdxAI)
    #print(self.armies)
    #print('Initialization done')

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

  def PlaceArmy(self, armyLbl, army):
    brd=self.board.ravel()
    brd[np.nonzero(brd==armyLbl)]=0
    armyIdx=np.nonzero(self.armiesLbl==armyLbl)[0][0]
    brd[army]=armyLbl
    self.armies[armyIdx,:]=army

  def Next(self,moveIdx,armyIdx):
    armyIdx+=1
    if armyIdx==self.armies.shape[0]:
      armyIdx=0
      moveIdx+=1
    return armyIdx,moveIdx

  def ManualMove(self,colBrd,brdDsp):
    (bd,w,maxIdx,armyIdx,army,armyLbl)=self.skConst
    cbd=colBrd.ravel()
    skArmy=np.zeros((1,),dtype=dtSeekArmy)[0]
    self.SeekMoves(skArmy)
    self.EvalMoves(skArmy)
    #self.ShowSeekArmy(skArmy)
    numMv=skArmy['numMoves']
    mvArr=skArmy['moves'][:numMv]
    uManIdx=np.unique(mvArr['manIdx'])
    print('possible moves:%d. select man idx (any key to exit)'%numMv)
    print(uManIdx)
    cbd[army]=armyLbl+((8+np.arange(army.shape[0]))<<8)
    self.printBrd(brdDsp,colBrd)
    cbd[army]=armyLbl
    try:
      manIdx=int(getkey())
    except (ValueError,TypeError):
      return None
    if not manIdx in uManIdx: return None
    numMv=skArmy['numMoves']
    mvArr=skArmy['moves'][:numMv]
    lst=np.nonzero(mvArr['manIdx']==manIdx)
    #print(mvArr)
    mvArr=mvArr[lst]
    cbd[army[manIdx]]=armyLbl+(1<<8)  #invert color
    for i,v in enumerate(mvArr):
      #cbr[v[1]]=armyLbl+((i+1)<<4)
      cbd[v[1]]=+((8+i)<<8)  #display number in army color
      if i<10:
        s=chr(ord('0')+i)
      else:
        s=chr(ord('a')-10+i)
      print('%s: %3d %.4g'%(s,v[1],v[2]))
    self.printBrd(brdDsp,colBrd)

    try:
      k=getkey()
      if k<='9':
        k=ord(k)-ord('0')
      else:
        k=ord(k)-ord('a')+10
      mv=mvArr[k]
    except IndexError:
      return None

    return mv

  def Run(self,brdDsp=0x08):
    '''press:
 x: quit
 h: help
 a: auto move loop
 b: best move (depth 1)
 l: move history
 u: undo one move
 s: show moves of one depth
 t: treesearch
 w: weight map'''

    #self.PlaceArmy(1,[110, 91, 22, 38, 39,108, 73, 92, 57, 58])
    #self.PlaceArmy(1,[231,250,266,232,213,284,267,233,196,248])
    print(Halma.Run.__doc__)
    moveIdx,armyIdx,=(1,0)
    self.printBrd(brdDsp)
    hist=[] #history of all movess
    for i in range(self.armiesLbl.shape[0]):
      hist.append((0,i,self.armies[i,:].copy(),None,None))

    while True:
      k=getkey()
      #k='s'
      if k=='x':   break
      elif k=='h': print(Halma.Run.__doc__);self.printBrd(brdDsp,)
      elif k=='b':#do best computer move depth=1
        self.SeekCalcConsts(armyIdx)
        (bd,w,maxIdx,armyIdx,army,armyLbl)=self.skConst
        mv=self.ExecBestMove() #quality
        posSum=self.distMap[0].ravel()[self.armies[0]].sum() #positional sum
        hist.append((moveIdx,armyIdx,army.copy(),mv[2],posSum))
        print('armyLbl:%d move:%d quality:%g posSum: %d'%(armyLbl,moveIdx,mv[2],posSum))
        print(army)
        self.printBrd(brdDsp)
        armyIdx,moveIdx=self.Next(moveIdx,armyIdx)
        if posSum==150:
          print('Finished!')
      elif k=='t':  #do best computer move depth=n
        self.SeekCalcConsts(armyIdx)
        (bd,w,maxIdx,armyIdx,army,armyLbl)=self.skConst
        mv=self.SeekTreeRoot(depth=1)
        posSum=self.distMap[0].ravel()[self.armies[0]].sum() #positional sum
        hist.append((moveIdx,armyIdx,army.copy(),mv[2],posSum))
        print('armyLbl:%d move:%d quality:%g posSum: %d'%(armyLbl,moveIdx,mv[2],posSum))
        print(army)
        self.printBrd(brdDsp)
        armyIdx,moveIdx=self.Next(moveIdx,armyIdx)
      elif k=='s':#show moves
        self.SeekCalcConsts(armyIdx)
        skArmy=np.zeros((1,),dtype=dtSeekArmy)[0]
        self.SeekMoves(skArmy)
        self.EvalMoves(skArmy)
        self.ShowSeekArmy(skArmy,brdDsp)
      elif k=='w':#show weight map
        self.printBrd(0x5,self.weightMap[0,:,:])
        self.printBrd(0x5,self.distMap[0,:,:])
      elif k=='u':  #undo
        print('undo')
        bd=self.board.ravel()

        numArmy=self.armiesLbl.shape[0]
        if len(hist)<=numArmy:
          continue # nothing to undo
        moveIdx,armyIdx,army,d,e=hist.pop()
        bd[army]=0
        a,aIdx,army,d,e=hist[-(numArmy)]
        self.armies[aIdx,:]=army
        bd[army]=self.armiesLbl[aIdx]
        self.printBrd(brdDsp)
      elif k=='l':  #log
        print('log')
        for h in hist:
          print(h)
      elif k=='a':  #manual move
        colBrd=np.ndarray(shape=self.board.shape,dtype=np.uint16)
        colBrd[:]=self.board
        while True:
          self.SeekCalcConsts(armyIdx)
          (bd,w,maxIdx,armyIdx,army,armyLbl)=self.skConst
          if armyIdx in self.armyIdxAI:
            mv=self.SeekTreeRoot(depth=1)
          else:
            mv=self.ManualMove(colBrd,brdDsp)
            if mv is None: break
            manIdx=mv[0]
            dstPos=mv[1]
            self.Move(army,manIdx,dstPos)
          colBrd[:]=self.board
          posSum = self.distMap[0].ravel()[self.armies[0]].sum()  # positional sum
          hist.append((moveIdx,armyIdx,army.copy(),mv[2],posSum))
          print('armyLbl:%d move:%d quality:%g posSum: %d' % (armyLbl,moveIdx,mv[2],posSum))
          print(army)
          armyIdx,moveIdx=self.Next(moveIdx,armyIdx)
        print('exit manual mode')
        self.printBrd(brdDsp)

  def SeekCalcConsts(self,armyIdx):
    board=self.board
    w=board.shape[0]
    bd=board.ravel()
    maxIdx=w*w
    armyIdx=armyIdx
    army=self.armies[armyIdx,:]
    armyLbl=armyLbl=self.armiesLbl[armyIdx]
    self.skConst=(bd,w,maxIdx,armyIdx,army,armyLbl)

  def SeekMoves(self,skArmy):
    #seeks all available moves of an army on the current board and stores the moves in skArmy
    verb=self.verbose
    # a b
    # c . d
    #   e f
    #Possible short moves:  =a=-18   b=-17   c=-1   d=+1   e=+17   f=+18
    #Possible jump moves:   =a=-2*18 b=-2*17 c=-1*2 d=+1*2 e=+17*2 f=+18*2
    i=0
    (bd,w,maxIdx,armyIdx,army,armyLbl)=self.skConst
    mv=skArmy['moves']
    #for man in army:
    for manIdx,man in enumerate(army):
      #TODO:resize moves if needed
      bd[man]=9; #self.print(1)
      js=i
      #short moves:
      p=man-w-1
      if p>0 and not bd[p]: mv[i][0]=manIdx;mv[i][1]=p;i+=1
      p=man-w
      if p>0 and not bd[p]: mv[i][0]=manIdx;mv[i][1]=p;i+=1
      p=man-1
      if p>0 and not bd[p]: mv[i][0]=manIdx;mv[i][1]=p;i+=1
      p=man+1
      if p<maxIdx and not bd[p]: mv[i][0]=manIdx;mv[i][1]=p;i+=1
      p=man+w
      if p<maxIdx and not bd[p]: mv[i][0]=manIdx;mv[i][1]=p;i+=1
      p=man+w+1
      if p<maxIdx and not bd[p]: mv[i][0]=manIdx;mv[i][1]=p;i+=1
      #long mv:
      jl=i
      i=Halma.SeekLongMoves(skArmy,bd,w,manIdx,maxIdx,mv,man,man,i)
      if i>js:
        if verb&0x04 and i>js:
          print('%d short %d long moves'%(jl-js,i-jl))
          print(mv[js:i].T)
          bd[mv[js:jl]['dstPos']]=0xa
          self.printBrd(0x2)
        bd[mv[js:i]['dstPos']]=0
      bd[man]=armyLbl
    skArmy['numMoves']=i

  def ExecBestMove(self,disp=0x00):
    (bd,w,maxIdx,armyIdx,army,armyLbl)=self.skConst
    skArmy=np.zeros((1,),dtype=dtSeekArmy)[0]
    self.SeekMoves(skArmy)
    self.EvalMoves(skArmy)
    mvArr=skArmy['moves']
    numMv=skArmy['numMoves']
    print('possible moves:%d'%numMv)
    mvQ=mvArr['quality']
    best=np.argmax(mvQ)
    mv=mvArr[best]
    manIdx=mv[0];dstPos=mv[1]
    self.Move(army,manIdx,dstPos,disp=disp)
    return mv

  @staticmethod
  def SeekLongMoves(skArmy,bd,w,manIdx,maxIdx,mv,man,pcur,i):
    w2=2*w
    #TODO:resize mv if needed
    p1=pcur-w-1; p2=pcur-w2-2
    if p2>0 and bd[p1]>0 and bd[p1]<=6 and not bd[p2]: mv[i][0]=manIdx;mv[i][1]=p2;bd[p2]=8;i=Halma.SeekLongMoves(skArmy,bd,w,manIdx,maxIdx,mv,man,p2,i+1)
    p1=pcur-w  ; p2=pcur-w2
    if p2>0 and bd[p1]>0 and bd[p1]<=6 and not bd[p2]: mv[i][0]=manIdx;mv[i][1]=p2;bd[p2]=8;i=Halma.SeekLongMoves(skArmy,bd,w,manIdx,maxIdx,mv,man,p2,i+1)
    p1=pcur-1  ; p2=pcur-2
    if p2>0 and bd[p1]>0 and bd[p1]<=6 and not bd[p2]: mv[i][0]=manIdx;mv[i][1]=p2;bd[p2]=8;i=Halma.SeekLongMoves(skArmy,bd,w,manIdx,maxIdx,mv,man,p2,i+1)
    p1=pcur+1  ; p2=pcur+2
    if p2<maxIdx and bd[p1]>0 and bd[p1]<=6 and not bd[p2]: mv[i][0]=manIdx;mv[i][1]=p2;bd[p2]=8;i=Halma.SeekLongMoves(skArmy,bd,w,manIdx,maxIdx,mv,man,p2,i+1)
    p1=pcur+w  ; p2=pcur+w2
    if p2<maxIdx and bd[p1]>0 and bd[p1]<=6 and not bd[p2]: mv[i][0]=manIdx;mv[i][1]=p2;bd[p2]=8;i=Halma.SeekLongMoves(skArmy,bd,w,manIdx,maxIdx,mv,man,p2,i+1)
    p1=pcur+w+1; p2=pcur+w2+2
    if p2<maxIdx and bd[p1]>0 and bd[p1]<=6 and not bd[p2]: mv[i][0]=manIdx;mv[i][1]=p2;bd[p2]=8;i=Halma.SeekLongMoves(skArmy,bd,w,manIdx,maxIdx,mv,man,p2,i+1)
    return i

  def EvalMoves(self,skArmy,disp=0x00):
    (bd,w,maxIdx,armyIdx,army,armyLbl)=self.skConst
    mvArr=skArmy['moves']
    numMv=skArmy['numMoves']
    verb=self.verbose&0x08
    #print('%d moves'%numMv)
    #print(mv.T)
    wm=self.weightMap[armyIdx].ravel()
    dm=self.distMap[armyIdx].ravel()
    for k in range(numMv):
      mv=mvArr[k]
      manIdx=mv[0];dstPos=mv[1]
      srcPos=self.Move(army,manIdx,dstPos,disp=disp)
      mvQ=wm[army].sum()
      #maxDiff=np.diff(np.sort(army)).max()/seek.w
      maxDiff=np.diff(np.sort(dm[army])).max()
      if maxDiff>2:
        mvQ-=maxDiff*1.
      mv[2]=mvQ
      if verb: print(mvQ[k])
      self.Move(army,manIdx,srcPos)

  def ReduceMoves(self,skArmy,depth):
    n=skArmy['numMoves']
    mv=skArmy['moves'][:n]
    if n>20:
      qSrt=np.argsort(mv['quality'])
      sel=qSrt[-20:]
    else:
      sel=np.arange(n,dtype=np.uint8)
    return sel

    #  skArmy['numMoves']=3

  def ShowSeekArmy(self,skArmy,disp=0):
    (bd,w,maxIdx,armyIdx,army,armyLbl)=self.skConst
    mvArr=skArmy['moves']
    numMv=skArmy['numMoves']
    sel=self.ReduceMoves(skArmy,0)

    colBrd=np.ndarray(shape=self.board.shape,dtype=np.uint16)
    colBrd[:]=self.board
    cbd=colBrd.ravel()
    cbd[army]=armyLbl+((8+np.arange(army.shape[0])<<8))
    self.printBrd(disp,colBrd)

    for i in range(numMv):
      manIdx=mvArr[i][0]
      dstPos=int(mvArr[i][1])
      q=mvArr[i][2]
      srcPos=int(army[manIdx])
      print('%d %3d %.4g'%(manIdx,dstPos-srcPos,q))
    verb=self.verbose&0x08
    print('%d moves'%numMv)

  def Move(self,army,manIdx,dstPos,board=None,disp=0x00):
    if board is None: board=self.board
    bd=board.ravel()
    srcPos=army[manIdx]
    lbl=bd[srcPos]
    bd[srcPos]=0
    army[manIdx]=dstPos
    bd[dstPos]=lbl
    if disp:
      self.printBrd(disp)
    return srcPos

  def printBrd(self,mode,board=None):
    # mode
    # 0x01: raw
    # 0x02: display bw board
    # 0x04: display as float values (0 value= out of board)
    # 0x08: display small colored board
    # 0x10: display small colored board
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
          elif k==0: ss+=' -'#'cd'
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
    if mode&8:
      R='\033[0m'  #reset
      C=( #color map
        '\033[38;5;237m',  #empty
        '\033[31m',  #army1
        '\033[32m',  #army2
        '\033[33m',  #army3
        '\033[34m',  #army4
        '\033[35m',  #army5
        '\033[36m',  #army6
      )
      I='X*+-%:+~0123456789abcdefghijklmnop'
      s=board.shape
      sz=self.size
      w=sz*4
      ofsS=sz*3*1
      for j in range(s[0]):
        ss = ' '*(w-j)
        soob=True#start out of board
        for i in range(s[1]):
          k=board[j,i]
          if k==7:
            if soob: ss+='  ';continue#'+-'
            else: break
          else:
            soob=False
            c=k&0xff # color index
            i=k>>8   # character index
            if c==0 and i:
              ss+=' '+I[i] #special char on empty field
            else:
              ss+=' '+C[c]+I[i]+R
        print(ss[ofsS:])
    if mode&0x10:
      R='\033[0m'  #reset
      C=( #color map
        '\033[38;5;237;7m',  #empty
        '\033[31;7m',  #army1
        '\033[32;7m',  #army2
        '\033[33;7m',  #army3
        '\033[34;7m',  #army4
        '\033[35;7m',  #army5
        '\033[36;7m',  #army6
      )
      I=' *+-%:+~0123456789abcdefghijklmnop'
      s=board.shape
      sz=self.size
      w=sz*4
      ofsS=sz*3*1
      for j in range(s[0]):
        ss1=ss2='   '*(w-j)
        soob=True#start out of board
        for i in range(s[1]):
          k=board[j,i]
          if k==7:
            if soob: ss1+='      ';ss2+='      ';continue#'+-'
            else: break
          else:
            soob=False
            c=k&0xff # color index
            i=k>>8   # character index
            if c==0 and i!=0:#empty with character
              ss1+='  '+C[c]+'   '+R+' '
              ss2+=' '+C[c]+'  '+R+I[i]+C[c]+'  '+R
            else:
              ss1+='  '+C[c]+'   '+R+' '
              ss2+=' '+C[c]+'  '+I[i]+'  '+R
        print(ss1[ofsS:])
        print(ss2[ofsS:])
        print(ss1[ofsS:])


  def SeekTreeRoot(self, depth=2,disp=0x00):
    #depth= search deph levels
    #reduce = maximal children per node
    verb=self.verbose&0x10
    (bd,w,maxIdx,armyIdx,army,armyLbl)=self.skConst
    self.bestTreeMove=0.
    self.bestDepth=0xffff
    if verb:
      self.treeMoves=[] #for debug
    skArmy=np.zeros((1,),dtype=dtSeekArmy)[0]
    self.SeekMoves(skArmy)
    self.EvalMoves(skArmy)
    sel=self.ReduceMoves(skArmy,depth)

    numMv=skArmy['numMoves']
    mvArr=skArmy['moves'][:numMv]
    print('possible moves:%d'%numMv)

    qArr=mvArr['quality']
    #for mvIdx in range(numMv):
    for mvIdx in sel:
      q=qArr[mvIdx]
      if q>=self.bestTreeMove:
        if q==self.bestTreeMove:
          if depth<=self.bestDepth:
            continue
          else:
            print('faster end')
        self.bestTreeMove=q
        self.bestIdx=mvIdx
        self.bestDepth=depth
        mv=mvArr[mvIdx]
        if verb:
          self.treeMoves.append(tuple(mv))
          print('SeekTreeRoot: rootMvIdx:%d mvIdx:%d depth:%d quality:%g'%(mvIdx,mvIdx,depth,q,))
          print(self.treeMoves)
          self.treeMoves.pop()
          print(army,mvArr)

    if depth>0: # and not winning move found
      #for k in range(numMv):
      for mvIdx in sel:
        mv=mvArr[mvIdx]
        manIdx=mv[0];dstPos=mv[1]
        srcPos=self.Move(army,manIdx,dstPos)
        if verb:
          self.treeMoves.append(tuple(mv))
          self.SeekTree(mvIdx,depth)
          self.treeMoves.pop()
        else:
          self.SeekTree(mvIdx,depth)
        srcPos=self.Move(army,manIdx,srcPos)

    mv=mvArr[self.bestIdx]
    manIdx=mv[0];dstPos=mv[1]
    print ('SeekTreeRoot %d, %g'%(self.bestIdx, self.bestTreeMove,))
    self.Move(army,manIdx,dstPos,disp=disp)
    return mv

  def SeekTree(self, rootMvIdx, depth):
    #depth= search deph levels
    #reduce = maximal children per node
    #print(depth)
    verb=self.verbose&0x10
    (bd,w,maxIdx,armyIdx,army,armyLbl)=self.skConst
    skArmy=np.zeros((1,),dtype=dtSeekArmy)[0]
    self.SeekMoves(skArmy)
    self.EvalMoves(skArmy)
    sel=self.ReduceMoves(skArmy,depth)

    numMv=skArmy['numMoves']
    mvArr=skArmy['moves'][:numMv]
    qArr=mvArr['quality']
    #for mvIdx in range(numMv):
    for mvIdx in sel:
      q=qArr[mvIdx]
      q=qArr[mvIdx]
      if q>=self.bestTreeMove:
        if q==self.bestTreeMove:
          if depth<=self.bestDepth:
            continue
          else:
            print('faster end')
        self.bestTreeMove=q
        self.bestIdx=rootMvIdx
        self.bestDepth=depth
        mv=mvArr[mvIdx]
        if verb:
          self.treeMoves.append(tuple(mv))
          print('rootMvIdx:%d mvIdx:%d depth:%d quality:%g'%(rootMvIdx,mvIdx,depth,q,))
          print(self.treeMoves)
          self.treeMoves.pop()
          print(army,mvArr)

    if depth>0: # and not winning move found
      #for mvIdx in range(numMv):
      for mvIdx in sel:
        mv=mvArr[mvIdx]
        manIdx=mv[0]
        dstPos=mv[1]
        srcPos=self.Move(army,manIdx,dstPos)
        if verb:
          self.treeMoves.append(tuple(mv))
          self.SeekTree(rootMvIdx,depth-1)
          self.treeMoves.pop()
        else:
          self.SeekTree(rootMvIdx,depth-1)
        self.Move(army,manIdx,srcPos)
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
    sys.stdout.write('\n')
    return k[0]

  def main():
    #v=0xffff
    v=0x00
    #v=0xf3
    #v=0x02
    halma=Halma(verbose=v)
    #halma=Halma(verbose=v,size=5)
    #halma.Init();exit(0)
    #halma.Init([1,4,5,6]);exit(0)
    #halma.Init([2,5])
    #halma.Init([1,2])
    #halma.SeekMoves(armyIdx=0)

    #halma.Init([1,])
    #halma.Init([1,3])
    #halma.Init([2,4],[0,],0)

    #halma.Init([1,2,3,4,5,6],[0,],1)
    #halma.Init([2,4],[0,],0)
    halma.Init([2,4],[0,],1)
    halma.Run(0x10)#0x08 #0x10
  main()

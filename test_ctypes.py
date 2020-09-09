import numpy as np
import ctypes as ct
#C-types array structures for searching tree
#--------------------------------------------
#https://stackoverflow.com/questions/40063080/casting-an-array-of-c-structs-to-a-numpy-array
#https://numpy.org/doc/stable/user/basics.rec.html
#https://numpy.org/doc/stable/reference/generated/numpy.ndarray.ctypes.html?highlight=ctypes#numpy.ndarray.ctypes


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
dtSeekArmy=np.dtype([('armyIdx',np.uint8),('moves',dtSeekMan, (128,)),('lenUsedMoves',np.uint8)],align=True)
dtSeekTree=np.dtype([('bestQuality',np.float),('bestIdx',np.uint8)],align=True)
sm=np.array([(2,3,4)],dtype=dtSeekMan)
np.ndarray(shape=(1,),dtype=dtSeekArmy)
np.empty(shape=(1,),dtype=dtSeekArmy)
sa=np.zeros(shape=(1,),dtype=dtSeekArmy)

sa[0]
sa[0]['moves']
sa=sa[0]  #take the item(0) of the array
mv=sa['moves']
mv.dtype.shape
mv.dtype.fields
mv[3]['manIdx']
mv[8]
manIdx=mv['manIdx']
manIdx[:]=12
mv

info=ctInfo()
info.w=4
print(info.w)
info=ctInfo(w=10)
info=ctInfo(ct.POINTER(ct.c_uint16)(),
            ct.POINTER(ct.c_uint8)(),
            7,0,
            ct.POINTER(ct.c_uint8)(),
            ct.POINTER(ct.c_float)(),
            ct.POINTER(ct.c_uint8)()
            ,9)

print(info)
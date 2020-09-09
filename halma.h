
//https://stackoverflow.com/questions/40063080/casting-an-array-of-c-structs-to-a-numpy-array

//   class SeekTreeC(ct.Structure):
//     _fields_=[("board",ct.POINTER(ct.c_uint8)),
//               ("w",ct.c_uint8), #width of board
//               ("real_data",ct.POINTER(ct.c_double)),
//               ("cmplx_data",ct.POINTER(ct.cmplx))]
//
//
//   class SeekNodeC(ct.Structure):
//     _fields_=[("seekTree",ct.POINTER(SeekTreeC)),
//               ("armyIdx",ct.c_uint8),
//               ("arr_len",ct.c_int),
//               ("real_data",ct.POINTER(ct.c_double)),
//               ]
//
// #ct.c_func.restype=info
// #ret_val=ct.c_func()
// #data=np.ctypeslib.as_array(ret_val.contents.real_data,shape=(info.contents.arr_len,))


typedef struct InfoC {
uint16 *armies;
uint8  *armiesLbl;
uint8   numArmies;  //1..6
uint8   lenArmy;    //default is 10=1+2+3+4

uint8  *board;
float  *weightmaps;
uint8  *distmap;
uint8   w; //width of board, weightmap, distmap etc.
} InfoC;

typedef struct SeekManC { // one move of one man
  uint8  manIdx;  //0..9
  uint16 dstPos;
  float  quality;
  //uint16 sumDMap;
  //uint16 maxDiff; ... and other stats possible
} SeekManC;

typedef struct SeekArmyC { // all moves on one army
  uint8     armyIdx;
  SeekManC  moves[128];   //array of all moves of this army,
                          //range is about 20-50 possible moves
  uint8     lenUsedMoves;
} SeekArmyC;

typedef struct SeekTreeC{
  float bestQuality;
  uint8 bestIdx;
} SeekTreeC;

SeekTreeRoot(uint8 depth)
{
  SeekTreeC st;
  st.bestQuality=0.f;
  SeekArmyC sa;
  SeekMoves(&sa);
  EvalMoves(&sa);
  ReduceMoves(&sa);

  for(mvIdx=0;mvIdx<sa.lenUsedMoves;mvIdx++)
  {
    Move(sa.moves[mvIdx])
    SeekTree(st,mvIdx,depth)
    UndoMove(sa.moves[mvIdx])
  }
}

SeekTree(SeekTreeC* st,rootMvIdx,depth)
{
  SeekArmyC sa;
  SeekMoves(&sa);
  EvalMoves(&sa);
  ReduceMoves(&sa);

  for(mvIdx=0;mvIdx<sa.lenUsedMoves;mvIdx++)
  {
    if (sa.moves[mvIdx].quality>st->bestTreeMove)
    {
      st->bestTreeMove=sa.moves[mvIdx].quality;
      st->bestIdx=rootMvIdx;
    }
  }
  if(depth>0) // and not winning move found
  {
    for(mvIdx=0;mvIdx<sa.lenUsedMoves;mvIdx++)
    {
      Move(sa.moves[mvIdx])
      SeekTree(st,rootMvIdx,depth-1)
      UndoMove(sa.moves[mvIdx])
    }
  }
  return;
}





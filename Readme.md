Board Representation
--------------------
```
 0|. . . . 1 . . . . . . . . . . . .
 1|. . . . 1 1 . . . . . . . . . . .
 2|. . . . 1 1 1 . . . . . . . . . .
 3|. . . . 1 1 1 1 . . . . . . . . .
 4|6 6 6 6 + + + + + 2 2 2 2 . . . .
 5|. 6 6 6 + + + + + + 2 2 2 . . . .
 6|. . 6 6 + + + + + + + 2 2 . . . .
 7|. . . 6 + + + + + + + + 2 . . . .
 8|. . . . + + + + + + + + + . . . .
 9|. . . . 5 + + + + + + + + 3 . . .
 a|. . . . 5 5 + + + + + + + 3 3 . .
 b|. . . . 5 5 5 + + + + + + 3 3 3 .
 c|. . . . 5 5 5 5 + + + + + 3 3 3 3
 d|. . . . . . . . . 4 4 4 4 . . . .
 e|. . . . . . . . . . 4 4 4 . . . .
 f|. . . . . . . . . . . 4 4 . . . .
 g|. . . . . . . . . . . . 4 . . . .
   ---------------------------------
   0 1 2 3 4 5 6 7 8 9 a b c d e f g

.=f= illegal place
+=0= empty place

board representation:
17x17 byre array
6 weight tables: one for every player


man=one marble
army=all 10 marbles of one player

Storage: armRep: positions of every man -> 6 armies at 10 mans
      or brdRep: board representation
      or both ?

-> to calculate possible moves -> loop on all man in armRep and seek on the brdRep
-> so both representations will be usefull

Store armRep in a 10x1 unsigned short array. The number is y+17*x. the position of a man

Store brdRep is a 17x17 unsigned byte array. number 1-6 is a man of the army, 0 is a empty field(+), f is a forbidden field(.)

First approach: move one army as fast as possible to the goal.
```

Interface
---------
```
select man 0..9
for the selected man show possible destinations with numbers 0..z
```

Moves
-----
```
# a b
# c . d
#   e f

#Possible short moves:
#=a=-18 b=-17 c=-1 d=+1 e=+17 f=+18
#
#Possible jump moves:
#=a=-2*18 b=-2*17 c=-1*2 d=+1*2 e=+17*2 f=+18*2
```




            .     .     .     .     1     .     .     .     .     .     .     .     .     .     .     .     .
         .     .     .     .     2     2     .     .     .     .     .     .     .     .     .     .     .
      .     .     .     .     3     3     3     .     .     .     .     .     .     .     .     .     .
   .     .     .     .     4     4     4     4     .     .     .     .     .     .     .     .     .
  5     5     5     5     5     5     5     5     5     5     5     5     5     .     .     .     .
     6     6     6     6     6     6     6     6     6     6     6     6     .     .     .     .
  .     7     7     7     7     7     7     7     7     7     7     7     .     .     .     .
     .     8     8     8     8     8     8     8     8     8     8     .     .     .     .
  .     .     9     9     9     9     9     9     9     9     9     .     .     .     .
     .    10    10    10    10    10    10    10    10    10    10     .     .     .
  .    11    11    11    11    11    11    11    11    11    11    11     .     .
    12    12    12    12    12    12    12    12    12    12    12    12     .
 13    13    13    13    13    13    13    13    13    13    13    13    13
     .     .     .     .    14    14    14    14     .     .     .     .
  .     .     .     .     .    15    15    15     .     .     .     .
     .     .     .     .     .    16    16     .     .     .     .
  .     .     .     .     .     .    17     .     .     .     .

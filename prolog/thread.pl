:- module(thread, [cell_size/2, stitch_length/4, usable_length/4]).
:- use_module(methods).

cell_size(Count, Millimetres) :- Millimetres is 25.4 / Count.

stitch_length(Type, Method, Count, Length) :-
    cell_size(Count, Cell), stitch_factor(Type, Method, Factor),
    Length is Cell * Factor.

usable_length(ThreadLength, TailLength, FoldParts, Usable) :-
    Parts is max(2, FoldParts),
    Usable is max(1.0, ThreadLength / Parts - TailLength).


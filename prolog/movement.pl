:- module(movement, [move/5, allowed_transition/4]).

move(X1-Y1, X2-Y2, horizontal, 1.0, Distance) :-
    Y1 =:= Y2, abs(X2-X1) =:= 1, Distance is 1.0.
move(X1-Y1, X2-Y2, vertical, 1.08, Distance) :-
    X1 =:= X2, abs(Y2-Y1) =:= 1, Distance is 1.0.
move(X1-Y1, X2-Y2, diagonal, 1.65, Distance) :-
    abs(X2-X1) =:= 1, abs(Y2-Y1) =:= 1, Distance is sqrt(2).

allowed_transition(A, B, Kind, Cost) :-
    move(A, B, Kind, Weight, Distance),
    Cost is Weight * Distance.


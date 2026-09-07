:- module(methods, [choose_method/3, stitch_factor/3]).

choose_method(Stitches, danish, 0.86) :-
    straight_ratio(Stitches, Ratio), Ratio >= 0.68, !.
choose_method(Stitches, mixed, 1.0) :-
    length(Stitches, Count), Count >= 5, !.
choose_method(_, english, 1.16).

straight_ratio([], 0.0).
straight_ratio([_], 0.0).
straight_ratio(Stitches, Ratio) :-
    findall(1, (select(A, Stitches, Rest), member(B, Rest), same_row_neighbour(A, B)), Hits),
    length(Hits, HitCount), length(Stitches, Count),
    Ratio is min(1.0, HitCount / max(1, Count)).

same_row_neighbour(S1, S2) :-
    X1 = S1.x, Y1 = S1.y, X2 = S2.x, Y2 = S2.y,
    Y1 =:= Y2, abs(X2-X1) =:= 1.

stitch_factor(full, danish, 3.55).
stitch_factor(full, mixed, 3.85).
stitch_factor(full, english, 4.15).
stitch_factor(half_forward, _, 1.55).
stitch_factor(half_backward, _, 1.55).
stitch_factor(_, _, 4.0).


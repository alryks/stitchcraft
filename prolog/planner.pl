:- module(planner, [plan_region/6]).
:- use_module(library(lists)).
:- use_module(movement).
:- use_module(methods).
:- use_module(thread).
:- use_module(expert_rules).

plan_region(Stitches, ThreadLength, Count, Tail, FoldParts, Plan) :-
    snake_order(Stitches, Ordered),
    choose_method(Ordered, Method, MethodCost),
    usable_length(ThreadLength, Tail, FoldParts, Usable),
    finish_reserve(Reserve), Limit is max(1.0, Usable - Reserve),
    build_segments(Ordered, Method, Count, Limit, Segments, Travel, Diagonals),
    sum_segment_lengths(Segments, TotalLength),
    length(Segments, SegmentCount), length(Ordered, StitchCount),
    Cost is MethodCost * (TotalLength + Travel * 2.0 + Diagonals * 3.0 + SegmentCount * 8.0),
    Plan = _{method:Method, segments:Segments, cost:Cost,
             stats:_{stitches:StitchCount, thread_segments:SegmentCount,
                     total_thread_mm:TotalLength, travel_mm:Travel,
                     diagonal_moves:Diagonals, long_jumps:0}}.

snake_order(Stitches, Ordered) :-
    predsort(compare_yx, Stitches, Sorted), group_rows(Sorted, Rows),
    alternate_rows(Rows, 0, Oriented), append(Oriented, Ordered).

compare_yx(Order, A, B) :-
    YA=A.y, YB=B.y, XA=A.x, XB=B.x,
    compare(CY, YA, YB), (CY == (=) -> compare(Order, XA, XB) ; Order=CY).

group_rows([], []).
group_rows([H|T], [[H|Same]|Rows]) :-
    Y=H.y, take_y(T, Y, Same, Rest), group_rows(Rest, Rows).
take_y([H|T], Y, [H|Same], Rest) :- H.y =:= Y, !, take_y(T, Y, Same, Rest).
take_y(Rest, _, [], Rest).

alternate_rows([], _, []).
alternate_rows([R|Rs], N, [O|Os]) :-
    (0 is N mod 2 -> O=R ; reverse(R,O)), N1 is N+1,
    alternate_rows(Rs, N1, Os).

build_segments([], _, _, _, [], 0.0, 0).
build_segments([S|Ss], Method, Count, Limit, Segments, Travel, Diagonals) :-
    stitch_len(S, Method, Count, FirstLength),
    consume(Ss, S, Method, Count, Limit, [S], FirstLength, Segments, Travel, Diagonals).

consume([], _, _, _, _, CurrentRev, Length, [Segment], 0.0, 0) :- make_segment(CurrentRev, Length, Segment).
consume([S|Ss], Prev, Method, Count, Limit, CurrentRev, Length0, Segments, Travel, Diagonals) :-
    stitch_len(S, Method, Count, StitchLength),
    P1=Prev.x-Prev.y, P2=S.x-S.y,
    ( allowed_transition(P1, P2, Kind, MoveCost),
      Length1 is Length0 + StitchLength + MoveCost,
      Length1 =< Limit
    -> consume(Ss, S, Method, Count, Limit, [S|CurrentRev], Length1, Segments, TravelRest, DiagRest),
       Travel is TravelRest + MoveCost,
       (Kind == diagonal -> Diagonals is DiagRest+1 ; Diagonals=DiagRest)
    ; make_segment(CurrentRev, Length0, Segment),
      stitch_len(S, Method, Count, NewLength),
      consume(Ss, S, Method, Count, Limit, [S], NewLength, Rest, Travel, Diagonals),
      Segments=[Segment|Rest]
    ).

stitch_len(Stitch, Method, Count, Length) :-
    (get_dict(stitch_type, Stitch, Raw) -> atom_string(Type, Raw) ; Type=full),
    stitch_length(Type, Method, Count, Length).

make_segment(Rev, Length, _{stitches:Ids, route:Route, length_mm:Rounded, start:Start, end:End}) :-
    reverse(Rev, Route), maplist(stitch_id, Route, Ids),
    Route=[First|_], last(Route, Last), Start=_{x:First.x,y:First.y}, End=_{x:Last.x,y:Last.y},
    Rounded is round(Length*10)/10.
stitch_id(S, Id) :- Id=S.id.

sum_segment_lengths(Segments, Total) :-
    findall(L, (member(S,Segments), L=S.length_mm), Ls), sum_list(Ls, Total).


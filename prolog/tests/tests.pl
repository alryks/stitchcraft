:- begin_tests(planner).
:- use_module('../movement').
:- use_module('../thread').
:- use_module('../planner').

stitches_line([
    _{id:"s1",x:0,y:0,stitch_type:"full"},
    _{id:"s2",x:1,y:0,stitch_type:"full"},
    _{id:"s3",x:2,y:0,stitch_type:"full"}
]).

test(horizontal_allowed) :- allowed_transition(0-0, 1-0, horizontal, 1.0).
test(long_diagonal_forbidden, [fail]) :- allowed_transition(0-0, 2-2, _, _).
test(cell_size) :- cell_size(14, S), S > 1.8, S < 1.82.
test(danish_line, [nondet]) :-
    stitches_line(S), plan_region(S, 1000, 14, 55, 2, P), P.method == danish,
    P.stats.thread_segments =:= 1.

:- end_tests(planner).
run_tests :- run_tests([planner]).

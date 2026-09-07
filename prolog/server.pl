:- use_module(library(http/thread_httpd)).
:- use_module(library(http/http_dispatch)).
:- use_module(library(http/http_json)).
:- use_module(library(http/http_cors)).
:- use_module(planner).

:- set_setting(http:cors, [*]).
:- http_handler(root(health), health, []).
:- http_handler(root(plan), plan, [method(post)]).

server(Port) :- http_server(http_dispatch, [port(Port)]).

health(_Request) :- reply_json_dict(_{status:"ok", service:"prolog"}).

plan(Request) :-
    cors_enable(Request, [methods([post])]),
    http_read_json_dict(Request, Body),
    defaults(Body, Region, Length, Count, Tail, Fold),
    plan_region(Region, Length, Count, Tail, Fold, Result),
    reply_json_dict(Result).

defaults(B, Region, Length, Count, Tail, Fold) :-
    Region=B.get(region),
    Length=B.get(thread_length_mm, 1000),
    Count=B.get(canvas_count, 14),
    Tail=B.get(tail_length_mm, 55),
    Fold=B.get(fold_parts, 2).


:- module(expert_rules, [transition_penalty/2, finish_reserve/1]).

transition_penalty(horizontal, 0.0).
transition_penalty(vertical, 0.08).
transition_penalty(diagonal, 0.65).
finish_reserve(18.0).


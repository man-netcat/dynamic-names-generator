grammar Rules;

// Parser rules
file: rule_object+ EOF;
rule_object: IDENTIFIER '=' '{' rule_body '}';
rule_body: (name_block | conditions_block | tags_block)*;

name_block: 'name' '=' STRING;
conditions_block: 'conditions' '=' condition_block;
tags_block: 'tags' '=' tag_block;

condition_block: '{' condition_expr* '}';
tag_block: '{' IDENTIFIER* '}';
condition_expr: logical_expr | key_value | block_expr;

logical_expr: ('OR' | 'AND') '=' condition_block
	| 'NOT' '=' (block_expr | condition_expr);

block_expr: '{' condition_expr* '}';

key_value: IDENTIFIER '=' ( value | condition_block);

value: IDENTIFIER | STRING | NUMBER | 'yes' | 'no';

// Lexer rules
IDENTIFIER: [a-zA-Z_][A-Za-z_0-9]*;
STRING: '"' (~["\\] | '\\' .)* '"';
NUMBER: [0-9]+;

WS: [ \t\r\n]+ -> skip;
COMMENT: '#' ~[\r\n]* -> skip;
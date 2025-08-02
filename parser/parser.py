from types import SimpleNamespace
from antlr4 import *
from RulesLexer import RulesLexer
from RulesParser import RulesParser
from RulesVisitor import RulesVisitor


class RuleBuilder(RulesVisitor):
    def __init__(self):
        super().__init__()
        self.rules = []

    def visitFile_(self, ctx):
        for ruleCtx in ctx.rule():
            self.visit(ruleCtx)
        return self.rules

    def visitRule(self, ctx):
        tag_name = ctx.IDENTIFIER().getText()
        rule_body = ctx.rule_body()

        name = None
        tags = []
        conditions = []

        for stmt in rule_body.children:
            first_token = stmt.getChild(0).getText()
            if first_token == "name":
                name = stmt.STRING().getText().strip('"')
            elif first_token == "tags":
                tags = [t.getText() for t in stmt.tag_block().IDENTIFIER()]
            elif first_token == "conditions":
                conditions = self._extractConditions(stmt.condition_block())

        rule = SimpleNamespace(
            tag_name=tag_name, name=name, tags=tags, conditions=conditions
        )
        self.rules.append(rule)

        print(f"Rule: {tag_name}, Name: {name}, Tags: {tags}, Conditions: {conditions}")

    def _extractConditions(self, conditionListCtx):
        conditions = []
        for condCtx in conditionListCtx.condition():
            key = condCtx.key().getText()
            valCtx = condCtx.value()

            if valCtx.scalarValue():
                val = valCtx.scalarValue().getText()
                conditions.append(f"{key} = {val}")
            else:
                nestedConditions = self._extractConditions(valCtx.conditionList())
                inner = " ".join(nestedConditions)
                conditions.append(f"{key} = {{ {inner} }}")

        return conditions


def read_rules(file_path: str):
    input_stream = FileStream(file_path, encoding="utf-8")
    lexer = RulesLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = RulesParser(stream)
    tree = parser.file_()

    builder = RuleBuilder()
    return builder.visit(tree)


if __name__ == "__main__":
    rules = read_rules("rules/rules.txt")
    for r in rules:
        print(
            f"Rule: {r.tag_name}, Name: {r.name}, Tags: {r.tags}, Conditions: {r.conditions}"
        )

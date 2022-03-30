#!/usr/bin/env python3

from pathlib import Path
import math
import regex
import fire
from datetime import datetime


def parse_entity_vhdl(path=Path()):
    """Parse entity definition of vhdl file at path.

    Returns Entity object.
    """
    content = ""
    with open(str(path), "r") as fd:
        for line in fd:
            content += line

    name = regex.findall(r"entity\s*(\w+)\s*is", content, regex.S | regex.M)
    if name:
        name = name[0]
    else:
        name = regex.findall(r"entity\s*(\{.*?\})\s*is", content, regex.S | regex.M)
        if not name:
            return None
        else:
            name = name[0]
    entity_def = regex.findall(
        r"entity\s*{0}.+end\s+{0};".format(name), content, regex.S | regex.M
    )
    if entity_def:
        entity_def = entity_def[0]
        ports = dict()
        generics = dict()
        for decl, content in regex.findall(
            r"(\w*)(\([^)(]*+(?:(?R)[^)(]*)*+\))", entity_def, regex.M | regex.S
        ):
            if "generic" in decl:
                generic_matcher = regex.compile(r"\s*?(\w+)\s*?:\s*(\w*)")
                for pair in regex.findall(generic_matcher, content):
                    generics[pair[0]] = pair[1]
            else:
                port_matcher = regex.compile(r"\s*?(\w+)\s*?:\s*(\w*?\s+\w+[^;\n]*)")
                for pair in regex.findall(port_matcher, content):
                    ports[pair[0]] = pair[1]

        return Entity(name, ports, generics)
    else:
        return None


def parse_template_vhdl(path=Path()):
    """Parse file given by path as template.

    Returns a template object.
    """
    content = ""
    with open(str(path), "r") as fd:
        for line in fd:
            content += line
    tokens_set = set()
    for token in regex.findall(r"\{0\.(.*?)\}", content, regex.S | regex.M):
        tokens_set.add(token)
    tokens = dict()
    for item in tokens_set:
        tokens[item] = ""
    entity = parse_entity_vhdl(path)
    if entity:
        return Template(entity.name, content, entity.ports, entity.generics, tokens)
    else:
        return None


class Entity:
    def __init__(self, name, ports=dict(), generics=dict()):
        self.name = name
        self.ports = ports
        self.generics = generics

    def __deflist(self, listname, elements):
        a = ""
        if elements:
            a += "{} (\n".format(listname)
            keys = list(elements)
            for i in range(0, len(elements)):
                value = elements[keys[i]]
                a += "   " + keys[i] + ": " + value
                if i + 1 < len(elements):
                    a += ";"
                a += "\n"
            a += ");\n"
        return a

    def __def(self):
        a = ""
        a += self.__deflist("generic", self.generics)
        a += self.__deflist("port", self.ports)
        return a

    def as_entity(self):
        a = "entity {} is\n".format(self.name)
        a += self.__def()
        a += "end entity {};".format(self.name)
        return a

    def as_component(self):
        a = "component {} is\n".format(self.name)
        a += self.__def()
        a += "end component {};".format(self.name)
        return a

    def as_instance(self, instance_name="", genassign=dict(), portassign=dict()):
        a = "{} : {}\n".format(instance_name, self.name)
        if self.generics and genassign:
            a += "generic map(\n"
            keys = list(self.generics.keys())
            for i in range(0, len(self.generics)):
                key = keys[i]
                a += "   {} => {}".format(key, genassign[key])
                if i + 1 < len(self.generics):
                    a += ","
                a += "\n"
            a += ")\n"
        if self.ports:
            a += "port map(\n"
            keys = list(self.ports.keys())
            for i in range(0, len(self.ports)):
                key = keys[i]
                a += "   {} => {}".format(key, portassign[key])
                if i + 1 < len(self.ports):
                    a += ","
                a += "\n"
            a += ");\n"
        return a

    def __str__(self):
        return self.as_entity()


class Template(Entity):
    def __init__(
        self, name, template_file, generics=dict(), ports=dict(), tokens=dict()
    ):
        super().__init__(name, generics, ports)
        self.template_file = template_file
        self.tokens = tokens

    def as_template(self):
        return self.template_file.format(**self.tokens)


def get_sources(path=Path()):
    sources = dict()
    for source in path.glob("./**/*.vhd"):
        entity = parse_entity_vhdl(source)
        if entity:
            sources[entity.name] = entity
    return sources


def get_templates(path=Path()):
    templates = dict()
    for source in path.glob("./**/*.vhd"):
        template = parse_template_vhdl(source)
        if template:
            template.name = source.name
            templates[template.name] = template
    return templates


class Generator:
    def __init__(self):
        self.name = ""
        self.keywords = dict()
        self.optionals = dict()

    def __str__(self):
        print(self.name)
        for k, v in self.keywords.items():
            print(k, v)
        print("optional:")
        for k, v in self.optional.items():
            print(k, v)

    def generate(self, **kwargs):
        return dict()


class EvenOdd(Generator):
    def __init__(self):
        super().__init__()
        self.keywords = {
            "input": "Name of input component",
            "output": "Name of output component",
            "CS": "Name of compare swap element",
            "template": "Name of template",
            "N": "Number of inputs. Must be power of 2",
        }
        self.optional = {
            "W": "Width of operands",
        }

    def __str__(self):
        for k, v in self.keywords:
            print(k, v)
        for k, v in self.optional:
            print(k, v)

    def connection_matrix(self, N):
        logp = int(math.log2(N))
        depth = logp * (logp + 1) // 2
        A = [[-1 for j in range(N)] for i in range(depth)]
        d = -1  # Current network depth index
        for p_e in range(0, logp):
            p = 2**p_e
            for k_e in range(p_e, -1, -1):
                k = 2**k_e
                d += 1
                for j in range(k % p, N - k, 2 * k):
                    for i in range(0, min(k, N - j - k)):
                        if math.floor((i + j) / (p * 2)) == math.floor(
                            (i + j + k) / (p * 2)
                        ):
                            # print(d, i + j, i + j + k)
                            A[d][i + j] = i + j + k
                            A[d][i + j + k] = i + j
        return A

    def generate(self, **kwargs):
        if not any(kw in kwargs.keys() for kw in self.keywords):
            print("Error: The following parameters are required:")
            print(self)
            return

        N = int(kwargs["N"])
        p = int(math.log2(N))
        depth = p * (p + 1) // 2
        top_name = "EvenOdd{}".format(N)
        bit_width = 8
        if "W" in kwargs.keys():
            bit_width = kwargs["W"]

        components = kwargs["input"].as_component() + "\n"
        components += kwargs["output"].as_component() + "\n"
        components += kwargs["cs"].as_component() + "\n"

        instances = ""
        generics = {"W": bit_width}
        ports = {
            "CLK": "CLK",
            "E": "E",
        }
        for i in range(N):
            specific = dict()
            specific["input"] = "input({})".format(i)
            specific["ser_output"] = "wire(0)({})".format(i)
            specific["LD"] = "S({})".format(0)

            instances += kwargs["input"].as_instance(
                "input_{}".format(i), generics, ports | specific
            )

        for i in range(N):
            specific = dict()
            specific["output"] = "output({})".format(i)
            specific["ser_input"] = "wire({})({})".format(depth, i)
            specific["ST"] = "S({})".format(depth - 1)
            instances += kwargs["output"].as_instance(
                "output_{}".format(i), generics, ports | specific
            )

        A = self.connection_matrix(N)
        for i in range(depth):
            for j in range(N):
                if A[i][j] > j:
                    a = j
                    b = A[i][j]
                    specific = dict()
                    specific["a"] = "wire({})({})".format(i, b)
                    specific["b"] = "wire({})({})".format(i, a)
                    specific["c"] = "wire({})({})".format(i + 1, b)
                    specific["d"] = "wire({})({})".format(i + 1, a)
                    specific["S"] = "S({})".format(i)
                    instances += kwargs["cs"].as_instance(
                        "CS_{}d_{}x{}".format(i, a, b), generics, ports | specific
                    )
        for i in range(depth):
            for j in range(N):
                if A[i][j] < 0:
                    bypass_beg = i
                    bypass_end = i
                    while bypass_end < depth and A[bypass_end][j] < 0:
                        A[bypass_end][j] = 0
                        bypass_end += 1
                        instances += "wire({})({}) <= wire({})({});\n".format(
                            bypass_end, j, bypass_beg, j
                        )
        tokens = {
            "top_name": top_name,
            "net_depth": depth,
            "num_inputs": N,
            "bit_width": bit_width,
            "components": components,
            "instances": instances,
            "date": datetime.now(),
        }
        kwargs["template"].tokens = tokens
        kwargs["template"].name = top_name

        return kwargs["template"]


class NetworkGenerator:
    def __init__(self):
        self.entities = dict()
        self.entities = get_sources(Path("src/"))
        self.templates = dict()
        self.templates = get_templates(Path("templates/"))

    def list(self, listtype=""):
        """List available components and templates.
        Searches "src/" for components, "templates/" for templates and lists
        results.
        Parameters:
            "components": list all available components with generics and ports.
            "templates": list all available templates with tokens,generics and
                        ports.
            "entity_name": list entity with generics and ports.
            "template_name": list template with tokens, generics and ports.
        """
        if listtype == "components":
            print("components:")
            for entity in self.entities.values():
                print(entity.name)

        elif listtype == "templates":
            print("templates:")
            for template in self.templates.values():
                print(template.name)

        elif listtype in self.entities.keys():
            entity = self.entities[listtype]
            print(entity.name + ":")
            if entity.generics:
                print("\tgenerics")
                for name, gtype in entity.generics.items():
                    print("\t\t" + name, ":", gtype)
            print("\tports")
            for name, ptype in entity.ports.items():
                print("\t\t" + name, ":", ptype)

        elif listtype in self.templates.keys():
            template = self.templates[listtype]
            print(template.name + ":")
            print("\t tokens:", template.tokens)
            if template.generics:
                print("\tgenerics")
                for name, gtype in template.generics.items():
                    print("\t\t" + name, ":", gtype)
            print("\tports")
            for name, ptype in template.ports.items():
                print("\t\t" + name, ":", ptype)

        else:
            print("components:")
            for entity in get_sources(Path("src/")).values():
                print("\t" + entity.name)
            print("templates:")
            for template in Path("templates/").glob("**/*.vhd"):
                print("\t" + template.name)

    def generate(self, generator_name="", **kwargs):
        if "evenodd" == generator_name.lower():
            names = ["input", "output", "cs"]
            for name in names:
                kwargs[name] = self.entities[kwargs[name]]
            kwargs["template"] = self.templates[kwargs["template"]]
            generator = EvenOdd()
            template = generator.generate(**kwargs)
            path = Path("build/{}.vhd".format(template.name))
            with open(str(path), "w") as fd:
                fd.write(template.as_template())
        else:
            print("Options: evenodd")

    def test(self):
        #        print(parse_entity_vhdl(Path("templates/SortNet.vhd")))

        gen = EvenOdd()
        gen.connection_matrix(8)


if __name__ == "__main__":
    fire.Fire(NetworkGenerator)

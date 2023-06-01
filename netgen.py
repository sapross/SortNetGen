#!/usr/bin/env python3

from pathlib import Path
import numpy as np
import math
import fire
import time

from scripts import vhdl
import scripts.network_generators as generators
from scripts.reporter import Reporter, Report
from scripts.template_processor import VHDLTemplateProcessor
from scripts.resource_allocator import Block_Allocator, is_ff
from scripts.plotter import PlotWrapper


def get_sources(path=Path()):
    sources = dict()
    for source in path.glob("./**/*.vhd"):
        entity = vhdl.parseVHDLEntity(source)
        if entity:
            sources[entity.name] = entity
    return sources


def get_templates(path=Path()):
    templates = dict()
    for source in path.glob("./**/*.vhd"):
        template = vhdl.parseVHDLTemplate(source)
        if template:
            template.name = source.name
            templates[template.name] = template
    return templates


def print_timestamp(title: str):
    time_str = "[%b %d %H:%M:%S]: "
    print(time.strftime(time_str) + title, end="")


class Interface:
    def __init__(self):
        self.start_time = time.perf_counter_ns()
        self.entities = dict()
        print_timestamp("Parsing sources...")
        self.entities = get_sources(Path("src/"))
        print(" done.")
        self.templates = dict()
        print_timestamp("Parsing templates...")
        self.templates = get_templates(Path("templates/"))
        print(" done.")
        self.__generator = None
        self.__network = None
        self.__ffreplacements = []
        self.__reporter = Reporter()

    def __del__(self):
        print_timestamp(
            "Finished after " + str(time.perf_counter_ns() - self.start_time) + "ns."
        )
        print()

    def __str__(self):
        return ""

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
        return self

    def generate(self, ntype: str, N: int, SW: int = 1):
        # Multiple generates withine one call should cause the
        # reporter to commit its aggregated stats to memory.
        if self.__network:
            self.__reporter.commit_report()

        valid_types = ["oddeven", "bitonic", "blank"]
        if "oddeven" == ntype.lower():
            print_timestamp("Generating Odd-Even-Network...")
            logp = int(math.ceil(math.log2(N)))
            self.__generator = generators.OddEven()
            self.__network = self.__generator.create(2**logp)
            self.__network = self.__generator.reduce(self.__network, N)
        elif "bitonic" == ntype.lower():
            print_timestamp("Generating Bitonic-Network...")
            logp = int(math.ceil(math.log2(N)))
            self.__generator = generators.Bitonic()
            self.__network = self.__generator.create(N)
            self.__network = self.__generator.reduce(self.__network, N)
        elif "blank" == ntype.lower():
            print_timestamp("Generating blank Network...")
            logp = int(math.ceil(math.log2(N)))
            depth = logp * (logp + 1) // 2
            self.__network = generators.Network(N, depth)
        else:
            print("Options: oddeven, bitonic, blank")
        if ntype.lower() in valid_types:
            self.__reporter.report_network(self.__network)
            print(" done.")
        return self

    def distribute_signal(self, signal_name: str, max_fanout: int):
        """Distributes the signal with the given name so that
        only a number of rows less than max_fanout is driven by the signal.
        """
        print_timestamp("Distributing signal '{}'...".format(signal_name))
        if self.__network:
            self.__network = self.__generator.distribute_signal(
                self.__network, signal_name, max_fanout
            )
        print(" done.")
        return self

    def reshape(self, output_config, num_outputs):
        if output_config.lower() not in ["max", "min", "median"]:
            print("Error: output_config options are max, min, median")
        else:
            print_timestamp(
                "Reshaping Network to {} with {} outputs...".format(
                    output_config, num_outputs
                ),
            )
            N = self.__network.get_N()
            if output_config.lower() == "max":
                self.__generator.prune(self.__network, set(range(0, num_outputs)))
                self.__network.output_config = "max"
            elif output_config.lower() == "min":
                self.__generator.prune(self.__network, set(range(N - num_outputs, N)))
                self.__network.output_config = "min"
            elif output_config.lower() == "median":
                lower_bound = N // 2 - num_outputs // 2
                upper_bound = N // 2 + (num_outputs + 1) // 2
                self.__generator.prune(
                    self.__network, set(range(lower_bound, upper_bound))
                )
                self.__network.output_config = "median"
            print(" done.")
            self.__reporter.report_network(self.__network)
        return self

    def prune(self, output_list, output_config="mixed"):
        print_timestamp(
            "Pruning Network outputs...",
        )
        self.__generator.prune(self.__network, output_list)
        self.__network.output_config = output_config
        print(" done.")
        self.__reporter.report_network(self.__network)
        return self

    def show_network(self):
        print(self.__network)
        return self

    def replace_ff(self, entity: str, limit=1500, entity_ff=48):
        print_timestamp(
            "Replacing FF with {} resource...".format(entity),
        )
        entity_obj = self.entities[entity]
        ralloc = Block_Allocator()
        ffrepl = ralloc.reallocate_ff(self.__network, entity_obj, limit, entity_ff)
        self.__reporter.report_ff_replacement(ffrepl)
        self.__ffreplacements.append(ffrepl)
        print(" done.")
        return self

    def write(
        self,
        path: str = "",
        cs: str = "SWCS",
        W: int = 8,
    ):
        # Templates: Network.vhd, Sorter.vhd, Test_Sorter.vhd
        template_names = ["Sorter.vhd", "Test_Sorter.vhd"]
        templates = [self.templates[n] for n in template_names]
        print_timestamp(
            "Writing templates ...",
        )
        cs_entity = self.entities[cs]
        if not path:
            name = self.__network.algorithm
            name += "_" + str(self.__network.get_N())
            name += "X" + str(len(self.__network.output_set))
            if self.__network.output_config:
                name += "_" + self.__network.output_config.upper()
            path = "build/{}/".format(name)
        path_obj = Path(path)
        path_obj.mkdir(parents=True, exist_ok=True)
        template_processor = VHDLTemplateProcessor()
        entities = {
            "CS": cs_entity,
            "Signal_Distributor": self.entities["SIGNAL_DISTRIBUTOR"],
        }
        kwargs = {"W": W, "ff_replacements": self.__ffreplacements}
        template_processor.process_network_template(
            path_obj / "Network.vhd",
            self.__network,
            self.templates["Network.vhd"],
            entities,
            **kwargs,
        )
        for temp in template_names:
            template_processor.process_template(
                path_obj / temp,
                self.__network,
                self.templates[temp],
                **kwargs,
            )
        print(" done.")
        print(
            "Wrote Network.vhd, "
            + ", ".join(template_names)
            + " to {}".format(str(path_obj))
        )
        print_timestamp("Writing reports ...")
        self.__reporter.commit_report()
        path = "build/report.csv"
        self.__reporter.write_report(path)
        print(" done.")
        print("Added data to build/report.csv.")
        return self

    def report_net(self, path=""):
        report = Report(self.__network)
        for key, value in report.content.items():
            print(key, value)
        return self

    def show_ff(self):
        layer = self.__network.con_net
        line = "|"
        for i in range(len(layer[0])):
            line += "{:<2}".format(i % 10)
            # line += "__".format(i % 10)
        line += "|"
        print(line)
        for i, stage in enumerate(layer):
            line = "|"
            for pair in stage:
                if is_ff(pair):
                    line += "+ "
                else:
                    line += "  "
            line += "| {}".format(i)
            print(line)

    def pretty_print(self):
        layer = self.__network.con_net
        for stage in layer:
            print(" " + "--" * len(stage) + "")
            for i, pair in enumerate(stage):
                if i < pair[1]:
                    end = pair[1]
                    if pair[0] == "F":
                        print(
                            " "
                            + "| " * (i)
                            + "==" * (end - i - 1)
                            + "=>"
                            + "| " * (len(stage) - end)
                            + " "
                        )
                    elif pair[0] == "R":
                        print(
                            " "
                            + "| " * (i)
                            + "<="
                            + "==" * (end - i - 1)
                            + "| " * (len(stage) - end)
                            + " "
                        )

    def show_ff_assign(self):
        layer = self.__network.con_net
        groups = self.__ffreplacements[0]
        line = "|"
        for i in range(len(layer[0])):
            line += "{:<2}".format(i % 10)
        line += "|"
        print(line)
        for i in range(len(layer)):
            line = "|"
            for j in range(len(layer[i])):
                if is_ff(layer[i][j]):
                    elem = "+ "
                    for k in range(len(groups)):
                        for point in groups[k]:
                            if np.all(np.equal(np.asarray((j, i)), point)):
                                elem = "{} ".format(k)
                                break
                    line += elem
                else:
                    line += "  "
            print(line)

    def plot(self):
        return PlotWrapper()


# a = Interface()
# a.test()

if __name__ == "__main__":
    fire.Fire(Interface)

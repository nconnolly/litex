# This file is Copyright (c) 2015-2016 Florent Kermarrec <florent@enjoy-digital.fr>
# License: BSD

import os
import subprocess

from litex.gen.fhdl.structure import _Fragment
from litex.build import tools
from litex.build.generic_platform import *


sim_directory = os.path.abspath(os.path.dirname(__file__))


def _build_tb(platform, vns, serial, template):
    def io_name(resource, subsignal=None):
        res = platform.lookup_request(resource)
        if subsignal is not None:
            res = getattr(res, subsignal)
        return vns.get_name(res)

    ios = """
#define SYS_CLK dut->{sys_clk}
""".format(sys_clk=io_name("sys_clk"))

    if serial == "pty":
        ios += "#define WITH_SERIAL_PTY"
    elif serial == "console":
        pass
    else:
        raise ValueError
    try:
        ios += """
#define SERIAL_SOURCE_VALID dut->{serial_source_valid}
#define SERIAL_SOURCE_READY dut->{serial_source_ready}
#define SERIAL_SOURCE_DATA  dut->{serial_source_data}

#define SERIAL_SINK_VALID dut->{serial_sink_valid}
#define SERIAL_SINK_READY dut->{serial_sink_ready}
#define SERIAL_SINK_DATA  dut->{serial_sink_data}
""".format(
    serial_source_valid=io_name("serial", "source_valid"),
    serial_source_ready=io_name("serial", "source_ready"),
    serial_source_data=io_name("serial", "source_data"),

    serial_sink_valid=io_name("serial", "sink_valid"),
    serial_sink_ready=io_name("serial", "sink_ready"),
    serial_sink_data=io_name("serial", "sink_data"),
    )
    except:
        pass

    try:
        ios += """
#define ETH_SOURCE_VALID dut->{eth_source_valid}
#define ETH_SOURCE_READY dut->{eth_source_ready}
#define ETH_SOURCE_DATA  dut->{eth_source_data}

#define ETH_SINK_VALID dut->{eth_sink_valid}
#define ETH_SINK_READY dut->{eth_sink_ready}
#define ETH_SINK_DATA  dut->{eth_sink_data}
""".format(
    eth_source_valid=io_name("eth", "source_valid"),
    eth_source_ready=io_name("eth", "source_ready"),
    eth_source_data=io_name("eth", "source_data"),

    eth_sink_valid=io_name("eth", "sink_valid"),
    eth_sink_ready=io_name("eth", "sink_ready"),
    eth_sink_data=io_name("eth", "sink_data"),
    )
    except:
        pass

    try:
        ios += """
#define VGA_DE dut->{vga_de}
#define VGA_HSYNC dut->{vga_hsync}
#define VGA_VSYNC dut->{vga_vsync}
#define VGA_R dut->{vga_r}
#define VGA_G dut->{vga_g}
#define VGA_B dut->{vga_b}
""".format(
    vga_de=io_name("vga", "de"),
    vga_hsync=io_name("vga", "hsync"),
    vga_vsync=io_name("vga", "vsync"),
    vga_r=io_name("vga", "r"),
    vga_g=io_name("vga", "g"),
    vga_b=io_name("vga", "b"),
    )
    except:
        pass

    content = ""
    f = open(template, "r")
    done = False
    for l in f:
        content += l
        if "/* ios */" in l and not done:
            content += ios
            done = True

    f.close()
    tools.write_to_file("dut_tb.cpp", content)


def _build_sim(platform, vns, build_name, include_paths, serial, verbose):
    include = ""
    for path in include_paths:
        include += "-I"+path+" "

    build_script_contents = """# Autogenerated by LiteX
    rm -rf obj_dir/
verilator {disable_warnings} -O3 --cc dut.v --exe dut_tb.cpp -LDFLAGS "-lpthread -lSDL" -trace {include}
make -j -C obj_dir/ -f Vdut.mk Vdut

""".format(
    disable_warnings="-Wno-fatal",
    include=include)
    build_script_file = "build_" + build_name + ".sh"
    tools.write_to_file(build_script_file, build_script_contents, force_unix=True)

    _build_tb(platform, vns, serial, os.path.join(sim_directory, "dut_tb.cpp"))
    p = subprocess.Popen(["bash", build_script_file], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output, _ = p.communicate()
    output = output.decode('utf-8')
    if p.returncode != 0:
        error_messages = []
        for l in output.splitlines():
            if verbose or "error" in l.lower():
                error_messages.append(l)
        raise OSError("Subprocess failed with {}\n{}".format(p.returncode, "\n".join(error_messages)))
    if verbose:
        print(output)


def _run_sim(build_name):
    run_script_contents = """obj_dir/Vdut
"""
    run_script_file = "run_" + build_name + ".sh"
    tools.write_to_file(run_script_file, run_script_contents, force_unix=True)
    r = subprocess.call(["bash", run_script_file])
    if r != 0:
        raise OSError("Subprocess failed")


class SimVerilatorToolchain:
    def build(self, platform, fragment, build_dir="build", build_name="top",
            toolchain_path=None, serial="console", run=True, verbose=True):
        os.makedirs(build_dir, exist_ok=True)
        os.chdir(build_dir)

        if not isinstance(fragment, _Fragment):
            fragment = fragment.get_fragment()
        platform.finalize(fragment)

        v_output = platform.get_verilog(fragment)
        named_sc, named_pc = platform.resolve_signals(v_output.ns)
        v_output.write("dut.v")

        include_paths = []
        for source in platform.sources:
            path = os.path.dirname(source[0]).replace("\\", "\/")
            if path not in include_paths:
                include_paths.append(path)
        include_paths += platform.verilog_include_paths
        _build_sim(platform, v_output.ns, build_name, include_paths, serial, verbose)

        if run:
            _run_sim(build_name)

        os.chdir("..")

        return v_output.ns

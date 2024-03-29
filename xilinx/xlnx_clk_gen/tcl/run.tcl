set partNumber $::env(XILINX_PART)
set boardName  $::env(XILINX_BOARD)
set board $::env(BOARD)

set ipName xlnx_clk_gen

create_project $ipName . -force -part $partNumber
set_property board_part $boardName [current_project]

create_ip -name clk_wiz -vendor xilinx.com -library ip -module_name $ipName

if {$board == "nexys4ddr"} {
    set sys_clk_freq 50
    set input_clk_source "Single_ended_clock_capable_pin"
    set input_clk_freq 100
} elseif {$board  == "vcu118"} {
    set sys_clk_freq 50
    set input_clk_source "Differential_clock_capable_pin"
    set input_clk_freq 300
} else {
    set sys_clk_freq 50
    set input_clk_source "Single_ended_clock_capable_pin"
    set input_clk_freq 200
}

set_property -dict [list CONFIG.PRIM_IN_FREQ $input_clk_freq \
                        CONFIG.PRIM_SOURCE $input_clk_source \
                        CONFIG.NUM_OUT_CLKS {1} \
                        CONFIG.CLKOUT2_USED {false} \
                        CONFIG.CLKOUT3_USED {false} \
                        CONFIG.CLKOUT4_USED {false} \
                        CONFIG.CLKOUT1_REQUESTED_OUT_FREQ $sys_clk_freq \
                        CONFIG.CLKIN1_JITTER_PS {50.0} \
                       ] [get_ips $ipName]

generate_target {instantiation_template} [get_files ./$ipName.srcs/sources_1/ip/$ipName/$ipName.xci]
generate_target all [get_files  ./$ipName.srcs/sources_1/ip/$ipName/$ipName.xci]
create_ip_run [get_files -of_objects [get_fileset sources_1] ./$ipName.srcs/sources_1/ip/$ipName/$ipName.xci]
launch_run -jobs 8 ${ipName}_synth_1
wait_on_run ${ipName}_synth_1

----------------------------------------------------------------------------------
-- Author: Stephan Proß
--
-- Create Date: 03/08/2022 02:46:11 PM
-- Design Name:
-- Module Name: TB_ShiftRegisters - Behavioral
-- Project Name: BitSerialCompareSwap
-- Tool Versions: Vivado 2021.2
-- Description: Simulation for I/O shift registers.
----------------------------------------------------------------------------------

library IEEE;
  use IEEE.STD_LOGIC_1164.all;
  use IEEE.NUMERIC_STD.all;

entity TB_IO_SHIFT_REGISTERS is
  --  Port ( );
  generic (
    W : integer := 8
  );
end entity TB_IO_SHIFT_REGISTERS;

architecture TB of TB_IO_SHIFT_REGISTERS is

  constant CKTIME        : time := 10 ns;

  signal clk             : std_logic;
  signal rst             : std_logic;
  signal e_i             : std_logic;
  signal load_i          : std_logic_vector(0 downto 0);
  signal store_i         : std_logic_vector(0 downto 0);
  signal input_i         : std_logic_vector(W - 1 downto 0);
  signal serial_i        : std_logic;
  signal output_i        : std_logic_vector(W - 1 downto 0);

begin

  CLOCK_PROCESS : process is
  begin

    clk <= '0';
    wait for CKTIME / 2;
    clk <= '1';
    wait for CKTIME / 2;

  end process CLOCK_PROCESS;

  LOAD_SHIFT_REGISTER_1 : entity work.load_shift_register
    generic map (
      W => W
    )
    port map (
      CLK        => clk,
      RST        => rst,
      LOAD       => load_i(0),
      E          => e_i,
      PAR_INPUT  => input_i,
      SER_OUTPUT => serial_i
    );

  STORE_SHIFT_REGISTER_1 : entity work.store_shift_register
    generic map (
      W => W
    )
    port map (
      CLK        => clk,
      RST        => rst,
      STORE      => store_i(0),
      E          => e_i,
      SER_INPUT  => serial_i,
      PAR_OUTPUT => output_i
    );

  TEST_PROCESS : process is
  begin

    rst     <= '1';
    e_i     <= '0';
    input_i <= (others => '0');
    load_i  <= "0";
    store_i  <= "0";
    wait for CKTIME/2;
    wait for CKTIME;
    rst     <= '0';
    e_i     <= '1';
    input_i <= "11001011";
    load_i  <= "1";

    for i in 0 to W - 2 loop

      wait for CKTIME;
      load_i <= "0";

    end loop;

    e_i     <= '0';
    wait for CKTIME * 2;
    e_i     <= '1';
    wait for CKTIME * 2;
    store_i <= "1";
    wait for CKTIME;
    store_i <= "0";
    assert (input_i = output_i)
      report "Mismatch:: " &
             " input_i= " & integer'image(to_integer(unsigned(input_i))) &
             " output_i= " & integer'image(to_integer(unsigned(output_i))) &
             " Expectation= input_i=output_i";

    wait;

  end process TEST_PROCESS;

end architecture TB;

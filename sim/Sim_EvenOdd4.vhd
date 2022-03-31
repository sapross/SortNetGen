-------------------------------------------------------------------------
-- Company:
-- Engineer:
--
-- Create Date: 03/10/2022 04:55:22 PM
-- Design Name:
-- Module Name: Sim_EvenOdd8 - Behavioral
-- Project Name:
-- Target Devices:
-- Tool Versions:
-- Description:
--
-- Dependencies:
--
-- Revision:
-- Revision 0.01 - File Created
-- Additional Comments:
--
----------------------------------------------------------------------------------


library IEEE;
use IEEE.STD_LOGIC_1164.all;

-- Uncomment the following library declaration if using
-- arithmetic functions with Signed or Unsigned values
use IEEE.NUMERIC_STD.all;

-- Uncomment the following library declaration if instantiating
-- any Xilinx leaf cells in this code.
--library UNISIM;
--use UNISIM.VComponents.all;

library work;
use work.CustomTypes.all;

entity Sim_EvenOdd8 is
end Sim_EvenOdd8;

architecture Behavioral of Sim_EvenOdd8 is
    constant W : integer := 8;
    constant Depth : integer := 3;
    constant N : integer := 4;

    component EvenOdd4 is
        generic (
            W : integer;
            Depth: integer;
            N : integer
        );
        port (
            CLK    : in  std_logic;
            E      : in  std_logic;
            R      : in  std_logic;
            input  : in  InOutArray(N-1 downto 0)(W-1 downto 0);
            output : out InOutArray(N-1 downto 0)(W-1 downto 0)
        );
    end component EvenOdd4;

    constant ckTime : time := 10 ns;
    signal CLK : std_logic;

    signal R : std_logic := '0';
    signal E : std_logic := '0';

    signal A : InOutArray(3 downto 0)(W-1 downto 0) := (X"5C", X"2B", X"A8", X"F2");
    signal A_Sorted : InOutArray(3 downto 0)(W-1 downto 0) := (X"F2", X"A8", X"5C", X"2B");
    signal B : InOutArray(3 downto 0)(W-1 downto 0) := (others => (others => '0'));

begin

    EvenOdd4_1: EvenOdd4
        generic map (
            W => W,
            Depth => Depth,
            N => N)
        port map (
            CLK    => CLK,
            E      => E,
            R      => R,
            input  => A,
            output => B);

    CLK_process : process
    begin
        CLK <= '0';
        wait for ckTime/2;
        CLK <= '1';
        wait for ckTime/2;
    end process;

    test_process : process

    begin


        E <= '0';
        wait for ckTime/2;
        R <= '1';
        wait for ckTime;
        R <= '0';
        E <= '1';
        wait for (W)*ckTime;
        A <= (X"42", X"F1", X"A1", X"F2");

        wait for 2*ckTime;
        for i in 0 to 3 loop
          assert B(i) = A_Sorted(i) report "Mismatch:: " &
            " i=      " & integer'image(i) &
            " B(i)=   " & integer'image(to_integer(unsigned(B(i)))) &
            " A_Sorted(i)= " & integer'image(to_integer(unsigned(A_Sorted(i)))) &
            " Expectation  B(i) = A_Sorted(i)";
        end loop;
        wait for ckTime;
        A_Sorted <= (X"F2", X"F1", X"A1", X"42");

        wait for W*ckTime;

        for i in 0 to 3 loop
          assert B(i) = A_Sorted(i) report "Mismatch:: " &
            " i=      " & integer'image(i) &
            " B(i)=   " & integer'image(to_integer(unsigned(B(i)))) &
            " A_Sorted(i)= " & integer'image(to_integer(unsigned(A_Sorted(i)))) &
            " Expectation  B(i) = A_Sorted(i)";
        end loop;

        wait;

    end process;

end Behavioral;
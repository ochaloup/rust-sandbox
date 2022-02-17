use thiserror::Error;

use solana_program::program_error::ProgramError;

#[derive(Error, Debug, Copy, Clone)]
pub enum ChkpCounterError {
    /// Invalid instruction
    #[error("Invalid Instruction")]
    InvalidInstruction,
    #[error("Amount Overflow")]
    AmountOverflow,
}

impl From<ChkpCounterError> for ProgramError {
    fn from(e: ChkpCounterError) -> Self {
        ProgramError::Custom(e as u32)
    }
}
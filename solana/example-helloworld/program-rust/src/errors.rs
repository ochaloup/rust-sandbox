use thiserror::Error;

use solana_program::program_error::ProgramError;

#[derive(Error, Debug, Copy, Clone)]
pub enum TestCounterError {
    /// Invalid instruction
    #[error("Invalid Instruction")]
    InvalidInstruction,
    #[error("Wrong Counter Client Timestamp data")]
    WrongCounterClientTimestamp,
    #[error("Amount Overflow")]
    AmountOverflow,
}

impl From<TestCounterError> for ProgramError {
    fn from(e: TestCounterError) -> Self {
        ProgramError::Custom(e as u32)
    }
}
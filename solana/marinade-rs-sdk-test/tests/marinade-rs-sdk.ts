import * as anchor from "@project-serum/anchor";
import { Program } from "@project-serum/anchor";
import { MarinadeRsSdk } from "../target/types/marinade_rs_sdk";

describe("marinade-rs-sdk", () => {
  // Configure the client to use the local cluster.
  anchor.setProvider(anchor.AnchorProvider.env());

  const program = anchor.workspace.MarinadeRsSdk as Program<MarinadeRsSdk>;

  it("Is initialized!", async () => {
    // Add your test here.
    const tx = await program.methods.initialize().rpc();
    console.log("Your transaction signature", tx);
  });
});

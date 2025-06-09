import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Send, StopCircle } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";

interface WelcomeScreenProps {
  handleSubmit: (task: string) => void;
  onCancel: () => void;
  isLoading: boolean;
}

export const WelcomeScreen: React.FC<WelcomeScreenProps> = ({
  handleSubmit,
  onCancel,
  isLoading,
}) => {
  const [inputValue, setInputValue] = useState("");

  const handleInternalSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputValue.trim()) return;
    handleSubmit(inputValue);
    setInputValue("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleInternalSubmit();
    }
  };

  const isSubmitDisabled = !inputValue.trim() || isLoading;

  return (
    <div className="flex flex-col items-center justify-center text-center px-4 flex-1 w-full max-w-3xl mx-auto gap-4">
      <div>
        <h1 className="text-5xl md:text-6xl font-semibold text-neutral-100 mb-3">
          Crogia Agent
        </h1>
        <p className="text-xl md:text-2xl text-neutral-400">
          Your autonomous development assistant
        </p>
        <p className="text-sm text-neutral-500 mt-2">
          Describe what you want to build, and I'll help you create it step by
          step.
        </p>
      </div>

      <div className="w-full mt-4">
        <form
          onSubmit={handleInternalSubmit}
          className="flex flex-col gap-2 p-3"
        >
          <div className="flex flex-row items-center justify-between text-white rounded-3xl rounded-bl-sm break-words min-h-7 bg-neutral-700 px-4 pt-3">
            <Textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Create a Flask web app with user authentication..."
              className="w-full text-neutral-100 placeholder-neutral-500 resize-none border-0 focus:outline-none focus:ring-0 outline-none focus-visible:ring-0 shadow-none md:text-base min-h-[56px] max-h-[200px]"
              rows={1}
            />
            <div className="-mt-3">
              {isLoading ? (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="text-red-500 hover:text-red-400 hover:bg-red-500/10 p-2 cursor-pointer rounded-full transition-all duration-200"
                  onClick={onCancel}
                >
                  <StopCircle className="h-5 w-5" />
                </Button>
              ) : (
                <Button
                  type="submit"
                  variant="ghost"
                  className={`${
                    isSubmitDisabled
                      ? "text-neutral-500"
                      : "text-blue-500 hover:text-blue-400 hover:bg-blue-500/10"
                  } p-2 cursor-pointer rounded-full transition-all duration-200 text-base`}
                  disabled={isSubmitDisabled}
                >
                  Start
                  <Send className="h-5 w-5" />
                </Button>
              )}
            </div>
          </div>
        </form>
      </div>

      <div className="text-xs text-neutral-500 space-y-1">
        <p>Powered by Docker containers and autonomous AI agents</p>
        <p>Each session runs in an isolated environment</p>
      </div>
    </div>
  );
};
